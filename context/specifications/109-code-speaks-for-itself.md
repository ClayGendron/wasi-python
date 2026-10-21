# 109 — Code speaks for itself: no document cited in a comment outside `src/`

- **Status:** **drafted 2026-10-20; re-applied and built 2026-10-21 on `1cf9762`** in worktree
  `spec/109-code-speaks-for-itself` from `d92307f` (branch `claude/gallant-ride-9nxxmn`: main plus
  the chain 103 to 108 landed, 108's build review and its disposition written in); first built
  2026-10-20 on `cecceed` from `b7a1250`, then re-applied on the chain's final tip (Decision 7);
  **reviewed before build: none required** (judge-only and comments-only; AGENTS.md rule 8), the
  build review follows. A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe by effect, build-class by the letter** (§5.7): comments in `scripts/`
  and in `.github/workflows/release.yml` change, so the files are build-class, and no code,
  string literal, artifact byte or recipe step changes. `MANIFEST` records every tracked file
  under `scripts/` by hash, so the next build's `MANIFEST` differs in those `recipe` lines and in
  nothing else. **A judge change** (a rules check, its scanner, its unit rows, an allowance, and
  comments across `tests/`): the lane accepts it with `--accept-judge`. Files: `AGENTS.md` (one
  parenthesis), `tests/harness/scan.py`, `tests/checks/test_rules.py`, `tests/unit/test_scan.py`,
  the comments and docstrings of 98 files under `tests/`, 47 under `scripts/`, 2 under `release/`
  and `.github/workflows/release.yml`, this specification.
- **Depends on:** nothing landed beyond main. It **lands last in the stacked chain 103 to 108**
  (the memo of Research, section 8): built on `b7a1250`, it is re-applied on the chain's tip
  before the wave (Decision 7), since every link edits comments in `tests/`. Spec 107's
  Decision 4 does the same job for `src/`; this specification covers `tests/`, `scripts/`,
  `release/` and the workflows only, and touches no file under `src/`.
- **Research it stands on:** `../research/2026-10-20-a-design-review-of-the-runner.md`, section
  8, its last paragraph: the owner's rule "code speaks for itself" (2026-10-20) and its counts
  (1,143 under `tests/`, 213 under `scripts/`, 4 under `release/`, a `grep` of `spec NNN` over
  every line). Its own measurements below, each labelled, on `b7a1250`.

## The problem

A comment that says `(spec 052, Decision 7)` tells a reader where a reason was once written and
not what it is. The reader leaves the file, finds the document, and hopes the decision was not
amended since. The owner's rule (AGENTS.md, "Code speaks for itself"): a code file names no
specification, memo, review, finding ID or `context/` path; the reason is written in words; a
document under `context/` may cite and link the code, so the trace runs from the documents to the
code and never back.

Measured on the base content (EXECUTED, `uv run python build/109/measure.py`, the scanner of
Decision 2 over the files of Decision 3, comments and docstrings only, on `b7a1250` plus the
check): **2,225 citations**: `tests/` 1,896, `scripts/` 272, `release/` 6, `.github/workflows/`
51. By kind: a specification 1,592, a review named or dated 242, a finding identifier 309, a
named finding of another letter 20, a `context/` path 22, the constitution's sections 21, the
word for a research write-up 13, a numbered question 6. The memo's `grep` counts every line,
string literals included, and one form only, so its numbers differ; this specification counts
what the rule reads.

## Decisions

### 1. The rule reads comments and docstrings; the judge reads `context/` as data

The rule is about what a reader is told, so it reads prose only: a Python file's comments and
docstrings, and the `#` comments of every other file. Code that reads a document as data (the
rules checks reading `context/specifications/`, the progress harness writing `context/progress/`,
the release's reads) is not a citation and stays. AGENTS.md's bullet gains one parenthesis, "(in
comments and docstrings; the judge reads `context/` as data)", so that it cannot be read as
forbidding those paths in code.

### 2. The check refuses these forms

`tests/harness/scan.py` gains `context_citation_hits(path)`, which returns `(line, rule, phrase)`
for each match in a file's prose, and `context_citation_files(root)`, the files of Decision 3.
The forms (`CITATION_RULES`):

| rule | refuses |
|---|---|
| `specification` | `\bspec(?:ification)?s?\s+\d{3}\b`, any case; and a bare number as a possessive, `0\d{2}'s` (`037's build`) |
| `constitution` | `\bconstitution\s*§`, any case; and a section numbered like `§4.15` (a licence's `§4(b)` is not) |
| `memo` | `\bmemo\b`, any case |
| `review` | `\breviews?\b` followed by a date `YYYY-MM-DD` or a path; and a review named by its kind: `build review`, `pre-build review`, `delta review`, `follow-up review`, `security review`, `integration review`, `re-review`, `confirmation's` |
| `question` | `\bquestion\s+\d+\b`, any case |
| `context path` | `\bcontext/[a-z_]+` |
| `finding` | `(?<![A-Za-z0-9_])[CDFLNS]\d{1,2}(?:\.\d+)?(?![A-Za-z0-9_])`, spec 107's |
| `named finding` | a finding of another letter (`M5`, `B1`, `R1`, `P6`, a mutation's `M18`) where `review`, `re-review` or `confirmation` names it |

The brief's forms are the first of each row. Three widen it, each found by the build's read
(EXECUTED, on the base content): the bare possessive (164 hits, `037's build`; a `spec 037's`
counts once for each form), a section sign with a numbered section (8, `§4.15`), and a review
named by its kind (239, `the build review`).
High, Medium and other letters are left out of the bare `finding` row because alone they are also
a milestone's or a chip's name (`M2`, `M1`). Python prose is read through `tokenize` (comment
tokens) and `ast` (the string token that opens a module, a class or a function); no other string
is prose. Other files: a line whose first non-blank character is `#`, and the part of a line
after a ` # `. **A citation broken across lines is read whole**: consecutive whole-line comments
are joined (their `#`s dropped), a docstring is read as one string, and a hit is reported on the
line it starts, its spaces made one. 35 citations on the base were broken that way (EXECUTED).

The check, `tests/checks/test_rules.py::test_code_outside_src_names_no_context_document`, reports
each hit as `path:line: rule: phrase`.

### 3. The files it reads

Every `.py`, `.sh`, `.toml`, `.yml` and `.yaml` file under `tests/` and `.github/workflows/`, and
every text file under `scripts/` and `release/` (the shell launchers there have no suffix; the
release's `.in` and `.txt` files are read as `#` comments). The workflow is included because its
comments cite specifications 51 times (EXECUTED); `src/` is spec 107's and is not read here.
Fixtures with other suffixes (`.ll`, `.expected`, `.platform`, `.txt`) and the upstream suites'
`.ini` files are not code and are not read.

### 4. Three rewriting rules, spec 107's

- **(a)** Delete only the citation and its connector: `(spec 052)`, `, spec 052,`, `per spec
  052`, `the review's F4.2`, `Spec 055, criterion 26: ` at a sentence's head (the next word then
  takes the capital the citation had). The sentence stays.
- **(b)** Where the citation was the whole explanation, or the actor of the sentence (`spec 078
  polls every call`), write the reason in words, drawn from the document it cited, which the
  builder reads. The landing notes list every such sentence with the document it stood on, so the
  trace moves into this specification.
- **(c)** Delete no sentence. Change no code, string literal, identifier, marker, golden, expected
  file, `tests/known_gaps.toml`, `tests/upstream/*.toml` or `context/progress/`. A string literal
  that cites a document (an assertion message, a message the runner or the judge emits and a test
  matches, a guest program held as a string, a generated file's text) is listed in the landing
  notes for spec 107 or its owner, not changed.

Only lines move where a rewritten sentence passed 100 columns: the paragraph is re-filled, its
words unchanged.

### 5. One allowance tuple: the judge's allowance files and the guest's own sources

`CONTEXT_CITATION_ALLOWED` in `tests/checks/test_rules.py` holds `(path, phrase, reason)`
entries; an entry admits that exact phrase in that file's prose. An entry that admits nothing
fails the check, so the tuple only shrinks. Its 62 entries are of two kinds, each with its reason
as a named constant:

- **`JUDGE_FILE`** (30 entries, 31 hits): the comments of `tests/known_gaps.toml` and
  `tests/upstream/*.toml`. Rule (c) and AGENTS.md rule 4 make those files' edits a judge change of
  their own, so a comment cleanup does not touch them.
- **`GUEST_INPUT`** (32 entries, 36 hits): the golden jobs `tests/jobs/*.py` (not `regen.py`) and
  the upstream suites' guest drivers `tests/upstream/drive.py` and `regrtest_drive.py`. Their
  bytes are the guest's input (Decision 8).

No other entry is added; a reviewer reads any addition.

### 6. String literals stay

Rule (c) keeps every string literal. The literals that cite a document fall in four kinds, which
the landing notes list by file and line: guest programs held as strings (their bytes are the
guest's input, and so its fuel), messages the judge or a build step prints and a check matches,
a generated C comment (`scripts/gen_inittab.py`), and fixtures that a scanner's unit rows read
(their text is the scanner's input). The first two are spec 107's or the owner's to reword with
the code that matches them.

### 7. A reproducible pass: a script, then a recorded hand pass

The mechanical cases are rewritten by a scratch script, `build/109/clean.py` (git-ignored, run
with `uv run python`), which edits only prose spans (the same reading as the check) one line at a
time, by rule (a) alone: a parenthesis that holds only citations, a citation at the head of a
parenthesis or a sentence, a citation after a `;` or `,` that closes a parenthesis, and `per
<citation>`. It never edits the files of Decision 5, never leaves a comment empty, and prints
each line it changes. Everything it leaves is read by hand, line by line, under rules (a) and (b),
and **the hand pass is recorded** as exact `(path, old, new[, document])` edits in
`build/109/hand/NN_*.py`, applied by `build/109/hand.py` (`--list-b` prints the rule (b) list),
with the re-fills of Decision 4 recorded beside them. Re-applied on the chain's tip, the cleanup
commits are dropped, `clean.py` and `hand.py` run on the new base, every edit that misses is
named, and the leftovers the check reports are read again; the check and its unit rows are
re-applied as they are.

### 8. The sources the guest runs keep their bytes

`tests/jobs/*.py` and the upstream suites' drivers run inside the guest. The draft expected a
shorter docstring to lower the guest's fuel by a little; the build measured otherwise (EXECUTED,
by node id, `tests/checks/test_v1_3_regex.py::test_regex_features_job_matches_native`, with the
frozen `v0.1.0a7` set): with the docstring 25 bytes shorter the job's fuel **rose** from
603,112,332 to 603,150,802 (plain, +6.4e-5) and from 373,260,750 to 373,334,247 (snapshot,
+1.97e-4, past the ratchet's 1e-4); the old job text on the new tree gives the old numbers back,
so the job's own bytes move it. A fuel row would move with no verdict to show for it, so these 24
files keep their base bytes and their citations are allowed (Decision 5). They are cleared by a
judge change that re-measures their fuel.

### 9. No verdict moves

The fast tier runs on the built commit with the frozen `v0.1.0a7` set, and `sameness.py`
compares its record with spec 103's built record (the chain's previous record on this base). The
only differences allowed are this specification's claims: the new check's node and the scanner's
unit rows.

## Intent

Every comment and docstring under `tests/`, `scripts/`, `release/` and the workflows gives its
reason in words. A rules check holds it, beside spec 107's for `src/`, and the only citations left
are in the judge's own allowance files and the guest's own sources, named one by one.

## Design

- **The scanner:** `CITATION_RULES` (Decision 2's table), `CITATION_SUFFIXES`,
  `_comment_blocks`, `_python_prose(text)`, `_hash_comments(text)`, `context_citation_hits(path)`,
  `context_citation_files(root)`, at the end of `tests/harness/scan.py`.
- **The check:** `test_code_outside_src_names_no_context_document`, `JUDGE_FILE`, `GUEST_INPUT`
  and `CONTEXT_CITATION_ALLOWED` in `tests/checks/test_rules.py`, after the specifications'
  shape checks.
- **The unit rows** (`tests/unit/test_scan.py`, eighteen): one parametrized row per form
  (fifteen cases), each seen in a Python docstring, a Python trailing comment, a shell comment
  line and a shell trailing comment; one negative row (a `context/` path and a citing literal in
  code, a `noqa` code and words with digits in a comment, a citing string in a shell command, a
  licence's section, a graph's number, a reviewed list, and a file that does not parse give no
  hit, while a lone `C99` in a comment does); one row for the files read; one row for a citation
  split across docstring lines and across comment lines, and a code line ending a block. Their
  fixtures are assembled from parts, so the unit file's own prose is never a hit.
- **The cleanup:** `build/109/clean.py`, then the recorded hand pass.

## Scope

In: the comments and docstrings of `tests/`, `scripts/`, `release/` and `.github/workflows/`;
the check, its scanner, its unit rows; the AGENTS.md parenthesis. Out: `src/` (spec 107);
`recipes/` and `pyproject.toml`'s comments (no rule reads them yet); `context/`; every string
literal (Decision 6); the judge's allowance files and the guest's own sources (Decision 5); a bare
`Decision N` or `criterion N` with no specification beside it (206 and 28 left, EXECUTED,
`build/109/residue.py`): they name a numbered part of no named document, the rule's forms do not
include them, and where this pass removed a specification it removed its decision with it;
`CHANGELOG.md` and the roadmap (the line is proposed in the landing notes).

## Acceptance criteria

1. **Seen failing first:** the check fails on `b7a1250` with the check, its scanner and its
   allowance in place and nothing else changed, and so does the widened check on the same content;
   both counts are kept in `build/109/seen-failing.txt`.
2. **Passes on the built commit**, with `CONTEXT_CITATION_ALLOWED` holding only the entries of
   Decision 5, every one used.
3. **Counts before and after** by tree, from the same scanner, in `build/109/hits-before.txt` and
   `build/109/hits-after.txt`, sorted by file and rule; after: 67, all in the files of Decision 5.
4. **The unit rows** (eighteen) pass; `tests/unit/test_scan.py` passes whole.
5. **Comments only:** for every file the cleanup commits change, the Python token stream with
   comments removed and docstrings blanked is the same before and after, and for every other file
   the lines that are not `#` comments are the same (`build/109/same-code.py`, EXECUTED, prints
   nothing).
6. **No protected file changes:** `git diff --stat b7a1250 -- tests/known_gaps.toml
   'tests/upstream/*.toml' tests/upstream/expected tests/upstream/python context/progress src` is
   empty, and so is the diff of the 24 guest sources of Decision 8.
7. **Rule (b) traced:** the landing notes list every sentence written under rule (b) with the
   document it stood on.
8. **The literals reported:** the landing notes list the citing string literals by file and line.
9. **Reproducible:** `clean.py` then `hand.py` on a copy of the base content give the built files,
   byte for byte, for every file but the check's own.
10. **The fast tier** on the built commit fails exactly the baseline's 83 nodes, and `sameness.py`
    against spec 103's built record prints nothing outside this specification's claims.
11. **Ruff:** `ruff check` and `ruff format --check` are green on `src/` and `tests/`.
12. **AGENTS.md** carries the parenthesis of Decision 1 and no other change.

## For the lane

- **Kind:** parallel-safe by effect, build-class by the letter; a judge change. The chain's last
  entry: re-applied on the chain's tip before the wave (Decision 7).
- **The dispatch:** none of its own; the chain's one dispatch on its final tip.
- **The claim list** and **the flags**: the landing notes, as the build ran them.

## One line

Every comment outside `src/` now says why in words, and a check keeps document numbers out of
code prose, the judge's allowance files and the guest's own sources named as the exceptions.

## Landing notes

Re-applied and built 2026-10-21 in the worktree `/home/user/wt/109`, branch
`spec/109-code-speaks-for-itself`, from the base `d92307f` (the PR branch
`claude/gallant-ride-9nxxmn`'s tip: 103 to 108 landed and renumbered, 108's build review and its
disposition written in). The first build (2026-10-20 on `cecceed` from `b7a1250`) was dropped to
its check commits and redone on this base, as Decision 7 asks. Every number here is EXECUTED on
this base or on the built commit, with its command; the outputs are kept under `build/109/` in
the worktree (git-ignored): `renumber-plan.txt`, `seen-failing-B.log`, `hits-before-B.txt`,
`hits-after-B.txt`, `clean-applied-B.txt`, `hand-applied-B.err`, `check-green-B.log`,
`scan-rules-B.log`, `fast.log`, `fast-lock-B.txt`, `built.json`, `claims.toml`,
`claims-chain.toml`, `sameness-108.txt`, `sameness-baseline-chain.txt`, `rule-b-B.txt`,
`literals-B.txt`, the scripts `clean.py`, `hand.py` with `hand/01_*.py` to `hand/17_*.py`,
`measure.py`, `same-code.py`, `literals.py`, `with-sigint.py`, `fast-B.sh`, and the first build's
records (`seen-failing.txt`, `hits-before.txt`, `hits-after.txt`, `regex-job-*.json`).

- **Commits, in the order built** (`git log --oneline d92307f..`): `ef0d06b` (this specification
  and the AGENTS.md parenthesis), `5af9484` (the check, its scanner, its first unit rows, seen
  failing), `f0b7083` (the check widened: split citations, bare numbers, named reviews, numbered
  sections), `b42e653` (this file renamed from 108 to 109 and its citations moved, since main
  reserved 102 for the release tier; the plan in `renumber-plan.txt`), `26dde7b` (the cleanup:
  comments and docstrings outside `src/` give their reasons in words), `1cf9762` (the allowance
  for the sources the guest runs and the `src/` check's own shapes), and the commit that carries
  this Status line and these notes. The built commit is `1cf9762`; the last commit touches only
  this file. `git diff --stat d92307f 1cf9762`: 150 files changed, 2,609 insertions, 1,806
  deletions (`tests/` 99 files, `scripts/` 47, `release/` 2, the workflow, `AGENTS.md`, this
  file). The first build's three text commits (`b0d5482`, `039cbc4`, `cecceed`) were dropped at
  the rebase and regenerated here; the two rebases (onto `0e145b7`, 107's landed tip, then
  onto `d92307f`) resolved one append hunk each, both sides kept: `tests/checks/test_rules.py`
  (107's line-ceiling and process-owner checks before this check's allowance and function) and
  `tests/harness/scan.py` (`import tokenize` beside 108's `import warnings`);
  `tests/unit/test_scan.py` merged on its own both times.
- **CI: none of its own; the chain's one dispatch on this tip** (the owner, 2026-10-20). This
  specification is the chain's last link, so that dispatch is its run; its id is the lane's to
  write here. The fast tier below is the build's judge.
- **Seen failing first** (`seen-failing-B.log`, criterion 1): the check on the base's content
  (`b42e653`: `d92307f` plus the check, its scanner, its unit rows and the allowance of the
  judge's thirty files' rows, nothing else changed): **2,208 findings**, digest `4c73c13fd534`.
  On `1cf9762` it passes with every allowance row used (`check-green-B.log`: 2 passed, the
  `src/` check beside it; criterion 2). The first build's two counts on `b7a1250` (1,758 and
  2,194) stay in `seen-failing.txt`.
- **Counts before and after** (`uv run python build/109/measure.py`, the final scanner;
  criterion 3): before, on `b42e653`, **2,239** (`tests/` 1,910, `scripts/` 272, `release/` 6,
  `.github/workflows/` 51; by rule: specification 1,590, finding 319, review 243, context path
  23, constitution 21, named finding 20, memo 17, question 6). The chain added 14 of them in
  `tests/checks/test_rules.py` (107's `src/` citation check documents its regexes with the
  shapes they match: nine finding-shaped tokens and the word "memo", four times) and 2 in 108's
  review scanners (`context/reviews/` and `reviews/…` named as paths); the four files 103 to
  108 added (`tests/harness/calls.py`, `tests/unit/test_lifecycles.py`, `test_process.py`,
  `test_runner_package.py`) carry none. After, on `1cf9762`, **81**, all under `tests/` and all
  in the allowance: 31 in the judge's allowance files (`tests/known_gaps.toml` 4,
  `tests/upstream/*.toml` 27), 36 in the guest's own sources (`tests/jobs/` 30,
  `tests/upstream/drive.py` 3, `regrtest_drive.py` 3), 14 in the `src/` check's documentation
  (`tests/checks/test_rules.py`); by rule: specification 61, finding 14, memo 4, context path 1,
  review 1. `scripts/`, `release/` and the workflow: 0. Files the cleanup changed: 98 under
  `tests/`, 47 under `scripts/`, 2 under `release/`, the workflow (148 files, 1,778 insertions,
  1,805 deletions).
- **The pass** (Decision 7; criterion 9): `clean.py` changed 1,230 lines in 143 files; the hand
  pass is 478 recorded edits in seventeen batches: 468 applied, 10 skipped as guest sources, 0
  missed. Run again from a scratch worktree at `b42e653`, the two give the cleanup commit's
  files byte for byte (`git diff --cached --stat 26dde7b` on the reproduced tree: empty). The
  first run on this base named four misses, each read and handled: two olds followed the chain
  (`test_rules.py`'s "Spec 102, Design" is "Spec 103" since the renumbering;
  `test_runner_sweep.py`'s "the removal is `_remove_tree`" is "the platform's `remove_tree`"
  since 107), and two entries were stale and removed (`test_runner_calls.py`'s "spec 015's epoch
  callback": 107 reworded the line itself, no citation left; `scripts/steps/35_stdlib_libs.sh`'s
  "(and its confirmation)": the final `clean.py` removes it itself). Two sentences the chain
  added are reworded by hand in batch 17: 108's release check named `context/reviews/` and its
  scanner named `reviews/NNN-<slug>-spec-YYYY-MM-DD.md`; each now says "among the reviews".
  The four review mentions the first build fixed in `cecceed` are in the batches now.
- **Comments only** (criterion 5): `uv run python build/109/same-code.py b42e653` after the
  cleanup commit prints nothing; on `1cf9762` it prints only `tests/checks/test_rules.py`, whose
  allowance tuple grew by 42 rows in the allowance commit. Criterion 6: `git diff --stat
  d92307f -- tests/known_gaps.toml 'tests/upstream/*.toml' tests/upstream/expected
  tests/upstream/python context/progress src` is empty, and so is the diff of the 25 golden
  jobs (`tests/jobs/*.py` but `regen.py`) and the two guest drivers. One reading the build
  review adds (its finding 1, EXECUTED with pyyaml): a `#` line inside a `run: |` block of the
  workflow is part of that step's script in the parsed document, so the parsed YAML at
  `d92307f` and at the built commit differ in exactly three values, the `verify` job's step 5
  and the two rebuild jobs' step 2, each by the shell comments inside the script and in no
  command; every other key and value is equal.
- **The sources the guest runs** (Decision 8): untouched, by `clean.py`'s own rule and
  `hand.py`'s skip, so there is no commit that puts their bytes back; the 24 that cite (22 jobs,
  `drive.py`, `regrtest_drive.py`) are in the allowance with the reason the first build
  measured (the regex job's fuel moved by +38,470 plain and +73,497 snapshot with a shorter
  docstring, `regex-job-*.json`). No fuel row may move, and none does (the sameness lines
  below: 0 fuel rows).
- **The allowance** (Decision 5, extended; `CONTEXT_CITATION_ALLOWED`, 72 rows, each with its
  reason, a stale row failing): 30 rows `JUDGE_FILE` (the known gaps and the upstream suites'
  allowances change only by a judge change of their own); 32 rows `GUEST_INPUT` (a source the
  guest runs: its bytes are the guest's input); 10 rows `SHAPE_SHOWN` for
  `tests/checks/test_rules.py` (`C6`, `C99`, `D3`, `F1`, `F3`, `F4.2`, `L1`, `N12`, `S3`,
  `memo`: the `src/` citation check documents its regexes by showing the shapes they match and
  refuse; the token is the rule's own vocabulary, not a citation of a document). The third
  reason is new to this build: 107's check landed after the first build, and its documentation
  must show the shapes (the AGENTS.md bullet: the judge reads `context/` as data). Every row is
  used (`measure.py`'s 81 hits are the rows' hits: 72 pairs, 0 unadmitted, 0 unused).
- **The fast tier** (criterion 10; `uv run pytest -m "not slow" -n 3 -q -p no:cacheprovider` on
  `1cf9762` with `WASI_PYTHON_ARTIFACTS` the frozen `v0.1.0a7` set, through `with-sigint.py`,
  under the machine's lock `build/fast-tier.lock`, taken at 00:38:49Z and freed at 00:43:26Z;
  `fast.log`): **83 failed, 2,459 passed, 52 skipped** in 276 s; the failed nodes are exactly
  the baseline's 83 (`build/baseline-a7/failing-nodes.txt`, a `diff` of the sorted node ids is
  empty). Unit suite: 1,948 rows (1,934 passed, 13 skipped, 1 failed:
  `test_the_walk_judges_links`, in the baseline's 83), 18 more than 108's reviewer record's
  1,930 (the eighteen scanner rows).
- **Sameness** (criterion 10, as the chain reads it), both verbatim, exit 0. Against 108's
  reviewer record (`uv run python tests/harness/sameness.py /home/user/wt/108/build/108/review.json
  build/109/built.json --claims build/109/claims.toml`):

  ```
  note: explained by claims: 109 2
  ```

  Against the chain's baseline (`uv run python tests/harness/sameness.py
  /home/user/wasi_python/build/baseline-a7/baseline.json build/109/built.json --claims
  build/109/claims-chain.toml`, the chain's claim list of 108 plus this specification's):

  ```
  note: explained by claims: 103 4 · 104 3 · 105 4 · 106 3 · 107 4 · 108 5 · 109 2
  ```

  0 fuel rows, 0 bytes rows, no verdict moved.
- **The claim list** (`build/109/claims.toml`, as run; `claims-chain.toml` is 108's chain list
  plus this one):

  ```toml
  [[claim]]
  spec = "109"
  new = [
    "tests/checks/test_rules.py::test_code_outside_src_names_no_context_document",
  ]
  units = 18
  ```

  109: **retired checks:** none. **Lost passes:** none. **Rows that grow:** none. **The judge
  hash changes** in `tests/harness/scan.py`, `tests/checks/test_rules.py`,
  `tests/unit/test_scan.py` and the comments of every changed file under `tests/`.
- **Rule (b) sentences** (criterion 7; `uv run python build/109/hand.py --list-b`), each with
  the document its words were drawn from (121; five more on the guest's sources are
  recorded in the batches and skipped):

  - `tests/checks/test_v1_4_embedding.py`: never freed; run now runs every program in a fresh __main__ ← spec 073 (run gives every program a fresh __main__ and unfreezes the heap)
  - `tests/checks/test_v1_4_embedding.py`: a call that has a `cancel` (the runner's stop from inside a host function), though the guest catches the door's error and computes on with no deadline. ← spec 011 (a host function stops its call without raising through wasmtime-py)
  - `tests/checks/test_v1_4_embedding.py`: reads now that # the runner polls every call, ← spec 078 (the runner polls every call's epoch, not only a deadline's)
  - `tests/checks/test_v1_4_embedding.py`: # The counts writable mounts add, all zero here. write_half = {"write": 0, "mkdir": 0, "remove": 0, "rmdir": 0, "rename": 0} ← spec 034 (writable mounts: the write half of the provider's calls)
  - `tests/checks/test_v1_4_embedding.py`: # read from the object; run(tools=…) is the bound form of the same host. ← spec 036 (tools in the runner: run(tools=…) builds the frame host)
  - `tests/checks/test_v1_4_embedding.py`: so this is not a check of the path a door call takes once it is overdue. ← spec 030 (a cancel during a door call that is overdue is named "cancelled")
  - `tests/checks/test_v1_4_embedding.py`: """The deep call chain's construction: each hop an object whose class's `__call__` is the next object, the ← spec 060 (a call chain of any depth, its review's eighth note)
  - `tests/checks/test_v1_2_hostile_guest.py`: whether it guards a change the safe-by-default work made or behaviour ← spec 006 (safe by default: the hostile guest, judged)
  - `tests/checks/test_v1_2_hostile_guest.py`: (a sleeping guest whose deadline was not kept waited 11.6 days), not a timing; a daemon thread cannot keep the test process alive. ← spec 010 (a sleeping guest keeps its deadline)
  - `tests/checks/test_v1_2_hostile_guest.py`: whatever route a program takes: each write-type call, by each route measured. ← research 2026-10-17-typed-grants, section 1 (read-only is enforced by one flag; its table of write-type calls)
  - `tests/checks/test_v1_2_hostile_guest.py`: stopped by the hook run_async registers for the interpreter's exit makes ← spec 015 (run from async code: the exit hook it registers)
  - `tests/checks/test_v1_2_hostile_guest.py`: writable=True)] # one provider, two places ← review 054-read-only-code-on-the-import-path-2026-10-18, finding 1 (a provider has no identity)
  - `tests/checks/test_v1_2_hostile_guest.py`: ( # CPython's own test_recursive_pickle ← spec 065 (CPython's own tests in the release)
  - `tests/unit/test_runner_mounts.py`: == 29 # the entry guard: an ended call runs no host ← spec 030, Decision 2 (the entry guard covers an ended call)
  - `tests/unit/test_runner_mounts.py`: with equal fuel (the release workflow's dry runs, EXECUTED). ← spec 063 (the release judges in parallel shards: its dry runs)
  - `tests/unit/test_runner_mounts.py`: to be made green there, never skipped. ← spec 076, Decision 9 (every row that never ran on Windows runs green there; none is skipped)
  - `tests/unit/test_runner_mounts.py`: and the three calls the cap on open files counts (path_open ← spec 068 (a cap on files open at once)
  - `tests/unit/test_runner_mounts.py`: ) # the eight provider calls a mount's record counts ← spec 034, Decision 11 (writable mounts: the record's eight keys)
  - `tests/unit/test_runner_mounts.py`: # The errno table of a provider's OSError, as measured: macOS and Linux EXECUTED, ← research 2026-10-18-a-providers-oserror-carries-its-errno (its table)
  - `tests/harness/scan.py`: "recipes/wasi-scipy.cross", # added for scipy ← spec 037 (scipy)
  - `tests/harness/scan.py`: "recipes/wasi-sklearn.cross", # added for scikit-learn ← spec 044 (scikit-learn)
  - `tests/harness/scan.py`: """Every rule of the release's provenance (each asset attested, then verified), as one line per breach, on the workflow without its comments; ← spec 009, Decision 6 (release provenance: every asset attested and verified)
  - `tests/harness/scan.py`: """Every rule of the build hosts' compiler table, one line ← spec 059, Decision 4 (the x86_64 rebuild runs natively: the compiler table's rules)
  - `tests/harness/scan.py`: "contourpy-build", # added for matplotlib's contours ← spec 043 (matplotlib's second milestone: contours)
  - `tests/harness/scan.py`: "scipy-build", # added for scipy ← spec 037 (scipy)
  - `tests/harness/scan.py`: "sklearn-build", # added for scikit-learn ← spec 044 (scikit-learn)
  - `tests/harness/scan.py`: """Every rule of the rebuild gate, as the x86_64 rebuild and the signing ties left it, one line per breach, ← spec 012, Decision 7, as specs 040 and 057 (Decision 4) left it (the same bytes from any host)
  - `tests/harness/scan.py`: """Every rule that ties what the release signs to what it built (rules 1 to 18), one line per breach, each starting with its rule's number, ← spec 057, Design (the release ties what it signs to what it built)
  - `tests/harness/scan.py`: (a rebase once redefined `CTRL_C` and lost two checks) ← spec 019 (its rebase redefined CTRL_C)
  - `tests/harness/scan.py`: """Every rule of a carried patch, on `recipes/patches/` ← spec 020, Decisions 6 and 7 (carried patches)
  - `tests/unit/test_runner_grants.py`: """Every raw preview1 write-type call, on a preopen ← research 2026-10-17-typed-grants, section 1 (its table of write-type calls)
  - `tests/unit/test_runner_grants.py`: (wasmtime behind the runner's guard, as every call ← spec 048 (the guard trampoline in front of wasmtime's own calls)
  - `tests/unit/test_runner_grants.py`: as the mounts' rows do). ← spec 032 (the mount rows)
  - `tests/unit/test_runner_grants.py`: (the guard carries wasmtime 49.0.3's rule; ← spec 048 (the guard trampoline carries wasmtime 49.0.3's rename rule)
  - `tests/harness/gather.py`: writes nothing to the progress history: only the lane accepts. It is the parallel judge's controller merge, across machines. ← spec 052 (the judge on several cores: the controller's merge)
  - `tests/harness/gather.py`: # a line older than the set's own sums has none ← spec 085 (gather checks what it trusts: the set's own SHA256SUMS hash)
  - `tests/checks/test_v1_5_rebuild_from_pins.py`: # The backend's try_table order: the research's reduced reproducer, copied under the judge's # paths and named by its hash, ← research 2026-10-19-the-try-table-order-in-llvm (the reduced reproducer)
  - `tests/checks/test_v1_5_rebuild_from_pins.py`: A line holding a reserved embedder's name is not written ← the reserved names list read as data (the embedder-neutral rule)
  - `tests/harness/paths.py`: "regex", # Apache-2.0 headed by its CNRI derivation ← spec 047, Decision 10 (regex's licence)
  - `tests/harness/paths.py`: any tracked change outside the progress history, or an untracked file it could see; an untracked .idea/ or a research draft is clean. ← none: the two folders the function reads, named in words
  - `tests/unit/test_regrtest.py`: # 542, and test_traceback since the 8 MiB guest stack closed its trap entry ← spec 078 (the runner runs each guest on a stack of its own, 8 MiB)
  - `tests/unit/test_regrtest.py`: # the 8 MiB guest stack closed the nine trap entries; its test_traceback added one class ← spec 078 (the runner runs each guest on a stack of its own, 8 MiB)
  - `tests/checks/test_rules.py`: (a rebase once lost two checks that way) ← spec 019 (its rebase lost two checks)
  - `tests/checks/test_rules.py`: (`patched_versions` in # the advisory's own JSON record). ← research 2026-10-18-wasmtime-49-advisories (the advisories' JSON records)
  - `tests/checks/test_rules.py`: (READ, wasmtime's list of releases) ← research 2026-10-18-wasmtime-49-advisories (its releases.txt)
  - `scripts/gen_inittab.py`: (as scikit-learn's build found: sklearn.utils._random) ← spec 044 (scikit-learn's build)
  - `scripts/gen_inittab.py`: (found at scikit-learn's build: ← spec 044 (scikit-learn's build)
  - `tests/unit/test_runner_async.py`: """A callback that continued undid the stops host functions record.""" ← spec 011 (a host function records its stop instead of raising)
  - `tests/unit/test_runner_async.py`: for the trap-handler guard to find; the guard is not what # this tests. ← spec 071 (a host guard against late signal handlers)
  - `tests/unit/test_runner_async.py`: so the trap-handler guard is set aside. ← spec 071 (a host guard against late signal handlers)
  - `tests/unit/test_gather.py`: """The two rows of the private root's read-only check name ← spec 084 (a private root never outlives its call: its read-only removal rows)
  - `tests/checks/test_v1_4_sessions.py`: """Python's shutdown runs when a session ends at its idle bound or its lifetime, and the ending's deadline is capped by what is left of the lifetime.""" ← spec 055, criterion 36 (and its close revision's review, finding 2: the ending's capped deadline)
  - `tests/checks/test_v1_4_sessions.py`: """A handler that never ends is stopped, by the session's own fuel when it is metered and by the shutdown's seconds when it is not; the session still closes.""" ← spec 055, criterion 37 (and its close revision's review, finding 5: the session's fuel bounds the ending)
  - `tests/checks/test_v1_4_sessions.py`: """After a stopped ending no export is called again, and after a Ctrl-C or an embedder's BaseException in the ending nothing is written back.""" ← spec 055, criterion 38 (and its close revision's review, finding 4: no write-back after a Ctrl-C)
  - `tests/checks/test_v1_4_sessions.py`: """A turn that returns after close() marked the session runs Python's shutdown before close() returns; a turn whose run raises ends "error" and skips it.""" ← spec 055, criterion 42 (and its build review's note on finding 3: the error row)
  - `tests/checks/test_v1_4_sessions.py`: """Criterion 40 (the cap on open files, per session: ← spec 068 (a cap on files open at once)
  - `tests/checks/test_v1_1_artifact_set.py`: (_binary(artifacts, "plain")) # the session exports' types ← spec 055, criterion 26 (the session exports' types)
  - `tests/checks/test_v1_1_artifact_set.py`: (_binary(artifacts, "snapshot")) # the session exports' types ← spec 055, criterion 26 (the session exports' types)
  - `tests/checks/test_v1_3_data_stack.py`: cheaper than the plain start. It was 8 # until run on the snapshot began to undo the freeze before finalizing, ← spec 073 and the owner's answer to question 103 (run on the snapshot undoes the freeze before finalizing)
  - `tests/checks/test_v1_3_lxml.py`: as the upstream facts sheet on libxml2's input without dup records them in its # evidence, ← context/upstream/8-libxml2-input-without-dup (evidence/encodings_whole_repertoire.txt)
  - `tests/checks/test_v1_3_matplotlib.py`: callbacks that the callback-signature scan found, ← spec 051 (the scan of callback signatures)
  - `tests/checks/test_v1_3_scipy.py`: until scipy's second milestone closed them: Matrix Market's thread pool, Sobol's temporary file, and the `ctypes` values four functions make. The same milestone adds the edges golden, ← spec 038 (scipy, the second milestone: the sandbox's edges)
  - `tests/checks/test_v1_4_public_api.py`: "Session", # bounded sessions ← spec 055 (bounded sessions)
  - `tests/harness/__init__.py`: It runs every check, prints the scoreboard by goal, compares the run with the last acceptance (the ratchet), and records an acceptance only when asked. ← spec 002 (the progress harness)
  - `tests/harness/artifacts.py`: "contourpy/util/_build_config.pyc", # made host-neutral at build time ← spec 043, Decision 4 (contourpy's build_config made host-neutral)
  - `tests/harness/callbacks.py`: (READ, in the callback scan's build), never a getter. ← spec 051 (the callback-signature scan)
  - `tests/harness/callbacks.py`: not read as a method (matplotlib's build): FreeType's ← spec 023 (matplotlib, the first milestone)
  - `tests/harness/constructors.py`: filled with pow(); matplotlib's build read their disassembly ← spec 023 (matplotlib, the first milestone)
  - `tests/harness/files.py`: """The mounts' fixtures: an in-memory provider ← spec 032 (mounts and the forwarder)
  - `tests/harness/files.py`: # Rows of the writable mounts' v1.4 write parity (`WRITE_PARITY`) ← spec 034 (writable mounts)
  - `tests/harness/files.py`: seen on windows-2025 in the release's dry runs). ← spec 063 (the release judges in shards: its dry runs)
  - `tests/harness/files.py`: the write half answers as a writable mount's provider does. ← spec 034, Decision 2 (writable mounts: the provider's write half)
  - `tests/harness/plugin.py`: the controller alone runs the landing lane's guards, writes ← spec 029 (the landing lane is guarded)
  - `tests/harness/plugin.py`: ("fuel", "bytes", "passes") # passes: an upstream suite's count ← spec 050, Decision 12 (numpy's and pandas' own tests: the passes metric)
  - `tests/harness/plugin.py`: if not is_worker(config): # the lane's guards run once, in the controller ← spec 029 (the landing lane is guarded)
  - `tests/harness/sameness.py`: residual serial runs show (the zip directory's zone-load check: 17 instructions in 8.7 million between a serial and a parallel run, the build's evidence). ← spec 035 (the zip's directory is read once: its zone-load check)
  - `tests/harness/sameness.py`: """A record sameness cannot read (a release record older than the merged release record).""" ← spec 092 (the judge reads a release record)
  - `tests/harness/sameness.py`: """A claim list that does not have the shape of `[[claim]]` tables.""" ← spec 092, Decision 5 (claim lists)
  - `tests/harness/scoreboard.py`: FUEL_TOLERANCE = 1e-4 # 0.01%: a run's fuel repeats exactly under the judge's own clock ← research 2026-10-16-a-host-supplied-clock-and-random-make-fuel-exact
  - `tests/harness/shards.py`: (the map the parallel judge's scheduler keeps) ← spec 052 (the judge on several cores)
  - `tests/harness/upstream.py`: fuel_facts: list[FuelFact] = field(default_factory=list) # recorded, never ratcheted ← spec 091 (numpy-core's layout-dependent fuel as a fact)
  - `tests/harness/wat.py`: # A snapshot as sets before bounded sessions were: no `turn` and no `shutdown`. ← spec 055 (bounded sessions)
  - `tests/harness/zips.py`: """The zips the zip-directory checks run on, made on the host. ← spec 035, Decision 11 (the zip's directory is read once)
  - `tests/harness/zips.py`: # The judge's two distributions: names the zip's own cannot clash with. ← spec 033 (the zip carries what packages need)
  - `tests/unit/test_async_tools.py`: """A frame host with its bound and its async tool loop, both counting ← specs 036 (tools in the runner: the bound) and 053 (async host functions: the tool loop)
  - `tests/unit/test_async_tools.py`: # Criterion 6: a late gate skips an async tool (the sync tools' rule, extended). ← spec 056 (the 0.1.0a4 security review's findings: a late gate skips a tool)
  - `tests/unit/test_build_scripts.py`: """A value instance has no memory to read, so its buffer refuses with the stand-in's OSError ← spec 033 (the ctypes stand-in's OSError)
  - `tests/unit/test_build_scripts.py`: ct.CFUNCTYPE(ct.c_int)) # scipy's cast, unchanged ← spec 037 (scipy: the cast it added to the stand-in)
  - `tests/unit/test_callbacks.py`: a single PyMethodDef (matplotlib's build: FreeType's BDF property table, ← spec 023 (matplotlib, the first milestone)
  - `tests/unit/test_guest.py`: # At the default step the resolution is the one CPython's tests were judged with, held by its own guard; ← spec 065 (CPython's own tests: the stated clock resolutions)
  - `tests/unit/test_landing_lane.py`: as `--accept` would since the history went into volumes. Returns ← spec 062 (the progress history stays small: volumes)
  - `tests/unit/test_runner_tools.py`: # the tool runs on, abandoned: a thread cannot be stopped ← spec 036 (tools in the runner: an abandoned tool runs on)
  - `tests/unit/test_sameness.py`: # Edge cases: merged statuses, missing sources, odd suites and arguments ← review 092-the-judge-reads-a-release-record-build-2026-10-20 (its findings 1 to 4)
  - `tests/unit/test_sameness.py`: """`--except` without `--claims` is an argument error, not a silent no-op.""" ← review 092-the-judge-reads-a-release-record-build-2026-10-20, finding 4
  - `tests/unit/test_sameness.py`: """The read-only-files need joins the CI needs' exception (gather.CI_NEEDS), on Windows only.""" ← spec 094 (the removal rows name their Windows need) and review 092's finding 1 (a block by a CI need is no difference)
  - `tests/unit/test_shards.py`: stand-in CPython trap entries: since the 8 MiB guest stack closed the nine, ← spec 078 (the runner runs each guest on a stack of its own)
  - `tests/unit/test_upstream.py`: == {"numpy", "pandas", "python"} # python: CPython's own tests ← spec 065 (CPython's own tests in the release)
  - `tests/unit/test_zip_directory.py`: """The zip directory's reader on the host: the recipe modules ← spec 035 (the zip's directory is read once)
  - `tests/checks/test_v1_4_embedding.py`: (the epoch callback's path and the entry guard). The default ← spec 030, Decision 2 (the entry guard covers an ended call)
  - `scripts/audit_openblas_void.py`: Adapted from the audit made before scipy's build. ← review 037-scipy-spec-2026-10-17, finding 3 (the audit this script adapts)
  - `scripts/openblas_make_void.py`: all `void`. Moved from the evidence folder of the research on OpenBLAS's return convention (a copy is kept there as evidence) unchanged ← research 2026-10-17-openblas-one-return-convention (its scripts/make_void.py)
  - `scripts/stage_scipy_cimports.sh`: for a package that cimports them # (scikit-learn and statsmodels): ← specs 044 (scikit-learn) and 045 (statsmodels), which use it
  - `scripts/steps/10_tools.sh`: with their hashes (pkgconf # for matplotlib), and ← spec 023 (matplotlib: pkgconf)
  - `scripts/steps/70_zip.sh`: (`--drop`, matplotlib's rule, which applies ← spec 023 (matplotlib: the --drop rule)
  - `tests/checks/test_v1_2_hostile_guest.py`: """Guards a change (the alphas' exception to safe defaults ends): the zip ← constitution §4.15 (safe by default; its exception for the alphas)
  - `tests/checks/test_v1_3_default_profile.py`: the form matplotlib's and scipy's checks use; ← specs 023 (matplotlib) and 037 (scipy)
  - `tests/checks/test_v1_3_scipy.py`: with nothing writable (the README says they work). Before scipy's second milestone, the first ← spec 038 (scipy, the second milestone)
  - `tests/checks/test_v1_4_embedding.py`: Exactly one dependency also makes the rule that each dependency has a written reason mechanical: ← constitution §4.13 (no dependency without a reason written in a specification)
  - `tests/checks/test_v1_4_embedding.py`: raises ImportError with the tool protocol's message; ← spec 031 (a tool protocol over the door)
  - `tests/harness/regrtest.py`: """This host's system key, as the release's shard records name platforms.""" ← spec 063 (the release judges in parallel shards)
  - `tests/harness/scan.py`: this file: the guarded lane's own and every # later one. ← spec 029 (the landing lane is guarded)
  - `tests/harness/scan.py`: and, from the guarded lane's judge on, says ← spec 029 (the landing lane is guarded)
  - `tests/release_shards.toml`: # Checks by node id: the recursion check on the wasmtime CLI needs ← spec 071 (deep recursion: its check on the pinned wasmtime CLI)
  - `tests/release_shards.toml`: nothing is retired). scikit-learn's # notice check ← spec 044 (scikit-learn)
  - `tests/unit/test_async_tools.py`: Built from the sync tools' self-locking `_proceed` ← spec 056 (the 0.1.0a4 security review's findings: the sync tools' _proceed)
  - `tests/unit/test_landing_lane.py`: whether the judge that wrote it is the guarded lane's (it knows this file) ← spec 029 (the landing lane is guarded)
  - `tests/unit/test_scan.py`: or one of the signing ties' widened rules. ← spec 057 (the release ties what it signs to what it built)
  - `tests/unit/test_shards.py`: Criterion 6's stand-in: the shard plan's path rule alone ← spec 063 (the release judges in parallel shards)
  - `scripts/assemble_artifacts.py`: # tier A: thirty pure-Python distributions, in the order they were chosen in ← spec 039, Decision 1 (tier A's list and its order)
  - `tests/checks/test_rules.py`: has its structural review of `src/` on file among the reviews, scoring the rubric's eight ← none: the reviews folder the check reads, named in words
  - `tests/harness/scan.py`: Status begins with built or landed, its own review before build, a file named `NNN-<slug>-spec-YYYY-MM-DD.md` among the reviews, and the file exists: the mirror of ← none: the reviews folder the scanner reads, named in words

- **String literals left** (criterion 8; rule (c); for spec 107 or the owner; 78 lines,
  the allowance tuple's own rows and the data paths under `context/` that code reads not
  listed): `scripts/gen_inittab.py:137` (spec 047); `tests/checks/test_rules.py:922` (memo); `tests/checks/test_v1_2_hostile_guest.py:75` (spec 017); `tests/checks/test_v1_2_hostile_guest.py:560` (spec 023); `tests/checks/test_v1_2_hostile_guest.py:1613` (spec 015); `tests/checks/test_v1_2_hostile_guest.py:2622` (055's, spec 055, spec 078); `tests/checks/test_v1_3_data_stack.py:232` (spec 069); `tests/checks/test_v1_3_data_stack.py:237` (spec 069); `tests/checks/test_v1_4_embedding.py:1172` (spec 017); `tests/checks/test_v1_4_embedding.py:1236` (032's, spec 030, spec 032, spec 052); `tests/checks/test_v1_4_embedding.py:2270` (017's, spec 017, spec 078); `tests/checks/test_v1_4_embedding.py:3076` (spec 052); `tests/checks/test_v1_5_rebuild_from_pins.py:306` (memo); `tests/checks/test_v1_5_rebuild_from_pins.py:376` (spec 086); `tests/harness/guest.py:584` (spec 081); `tests/harness/history.py:258` (spec 062); `tests/harness/litter.py:55` (spec 089); `tests/harness/litter.py:164` (spec 089); `tests/harness/litter.py:213` (spec 089); `tests/harness/paths.py:344` (constitution §); `tests/harness/pins.py:98` (spec 090); `tests/harness/plugin.py:94` (spec 002); `tests/harness/plugin.py:108` (spec 063); `tests/harness/plugin.py:151` (constitution §); `tests/harness/plugin.py:182` (spec 029); `tests/harness/plugin.py:193` (spec 029); `tests/harness/plugin.py:204` (spec 002); `tests/harness/plugin.py:294` (spec 063); `tests/harness/plugin.py:516` (spec 052); `tests/harness/plugin.py:542` (build review); `tests/harness/sameness.py:114` (092's, build review); `tests/harness/sameness.py:117` (spec 092); `tests/harness/sameness.py:118` (spec 092); `tests/harness/sameness.py:423` (spec 092); `tests/harness/scan.py:1545` (057's, spec 057); `tests/harness/scan.py:1794` (spec 085); `tests/harness/scan.py:2338` (spec 026); `tests/harness/scan.py:3004` (memo); `tests/harness/scan.py:3027` (re-review); `tests/harness/scoreboard.py:35` (spec 091); `tests/harness/scoreboard.py:232` (spec 062); `tests/harness/scoreboard.py:301` (spec 062); `tests/unit/test_build_progress.py:1087` (spec 079); `tests/unit/test_landing_lane.py:353` (memo); `tests/unit/test_landing_lane.py:372` (reviews/); `tests/unit/test_landing_lane.py:395` (constitution §); `tests/unit/test_landing_lane.py:626` (build review); `tests/unit/test_landing_lane.py:677` (constitution §); `tests/unit/test_patches.py:267` (spec 090); `tests/unit/test_pins.py:87` (spec 090); `tests/unit/test_pins.py:89` (spec 090); `tests/unit/test_sameness.py:221` (spec 092); `tests/unit/test_sameness.py:227` (spec 092); `tests/unit/test_scan.py:203` (memo); `tests/unit/test_scan.py:244` (reviews/); `tests/unit/test_scan.py:247` (reviews/); `tests/unit/test_scan.py:254` (reviews/); `tests/unit/test_scan.py:304` (reviews/); `tests/unit/test_scan.py:309` (reviews/); `tests/unit/test_scan.py:311` (reviews/); `tests/unit/test_scan.py:319` (reviews/); `tests/unit/test_scan.py:322` (reviews/); `tests/unit/test_scan.py:325` (reviews/); `tests/unit/test_scan.py:2102` (spec 085); `tests/unit/test_scan.py:2274` (constitution §); `tests/unit/test_scan.py:2275` (memo); `tests/unit/test_scan.py:2276` (review 2026-10-19); `tests/unit/test_scan.py:2277` (review reviews/); `tests/unit/test_scan.py:2278` (question 95); `tests/unit/test_scan.py:2280` (build review); `tests/unit/test_scan.py:2282` (Confirmation's, Confirmation's M5); `tests/unit/test_scipy_build.py:306` (090's, spec 090); `tests/unit/test_several_cores.py:434` (spec 052); `tests/unit/test_shards.py:210` (spec 001, spec 065); `tests/unit/test_shards.py:282` (spec 065); `tests/unit/test_shards.py:283` (spec 065, spec 099); `tests/unit/test_upstream.py:745` (reviews/); `tests/unit/test_upstream.py:911` (reviews/). They are guest programs held as strings (`test_v1_2_hostile_guest.py`,
  `test_v1_4_embedding.py`), messages the judge prints and a check matches (`plugin.py`,
  `sameness.py`, `scoreboard.py`, `litter.py`, `pins.py`, `history.py`, `guest.py`, `paths.py`,
  `scan.py`), a generated C comment (`gen_inittab.py`), and fixtures a scanner's unit rows read
  (`test_scan.py`, `test_landing_lane.py`, `test_upstream.py`, `test_shards.py`,
  `test_sameness.py`, `test_pins.py`, `test_patches.py`, `test_scipy_build.py`,
  `test_several_cores.py`, `test_build_progress.py`).
- **Other criteria:** `uv run ruff check src tests` and `uv run ruff format --check src tests`
  green (criterion 11); `uv run mypy --strict src/wasi_python`: no issues in 18 files; `uv run
  pytest tests/unit/test_scan.py tests/checks/test_rules.py -q -p no:cacheprovider` under the
  frozen set: 287 passed, 3 skipped, 1 failed (`test_version_states_the_platform_semantics`,
  the older set's, in the baseline's 83; `scan-rules-B.log`); `git diff d92307f -- AGENTS.md`
  is the one parenthesis (criterion 12); `test_specifications_have_their_header_and_sections`
  and `test_specifications_have_no_open_question` pass with this file.

### For the lane, as built

- **Kind:** parallel-safe by effect, build-class by the letter (comments in `scripts/` and the
  workflow change; `MANIFEST`'s recipe lines move with them); a judge change. The chain's last
  link, re-applied on 108's reviewed tip; it touches no file under `src/`, no allowance file,
  no golden or expected file, no guest-run source.
- **The claim list** (each line starts "109:"):
  - 109: **new checks (1 node), passing, no fuel, no bytes:**
    `tests/checks/test_rules.py::test_code_outside_src_names_no_context_document`.
  - 109: **unit rows:** `tests/unit/test_scan.py` gains eighteen rows (the citation scanner):
    the suite's count rises by eighteen.
  - 109: **retired checks:** none. **Lost passes:** none. **Grown rows:** none.
  - 109: **the judge hash changes** in `tests/harness/scan.py`, `tests/checks/test_rules.py`,
    `tests/unit/test_scan.py` and every file under `tests/` whose comments changed.
- **The flags** (paste-safe; no `--accept-growth`):

  ```
  --accept "109: comments and docstrings under tests/, scripts/, release/ and the release workflow give their reasons in words: no specification, constitution section, research write-up, review, numbered question, context/ path or finding identifier; comments only, no code, literal, golden, allowance file or guest-run source changed; the frozen set's verdicts the same"
  --accept-judge "109: a rules check that no comment or docstring under tests/, scripts/, release/ or .github/workflows/ cites a project document, read through tokenize and ast for Python and through # comments elsewhere, a citation split across lines read whole; an allowance of 72 entries, each with its reason: the judge's allowance files (known_gaps.toml, tests/upstream/*.toml; 30), the guest's own sources (tests/jobs/*.py, tests/upstream/drive.py, regrtest_drive.py; 32) and the src/ citation check's own documentation of the shapes its regexes match (10), a stale entry failing; eighteen unit rows for the scanner; comments across tests/ rewritten; no existing expectation edited"
  ```

- **Dry-run needs:** none beyond the chain's one dispatch on this tip. The check runs where
  `test_rules.py` runs (macOS and Linux, the `own-rest` shard); it reads files only.
- **CHANGELOG line proposed** (not written; the file is the lane's), under the one unreleased
  section: *Code speaks for itself outside `src/` (spec 109). Comments and docstrings under
  `tests/`, `scripts/`, `release/` and the release workflow give their reasons in words, with no
  specification number, review, finding identifier or `context/` path; a rules check holds it,
  with the judge's allowance files, the guest's own sources and the `src/` check's own
  documentation of its shapes named as the exceptions. No code, behaviour, fuel or artifact
  byte changes; `MANIFEST`'s recipe hashes of `scripts/` move with their comments.*
- **Roadmap:** untouched by this build. The build review (finding 2) asks the lane for one
  line, since the owner's rule's leftovers have no specification that owns them: the 78
  string-literal lines above, several of them read by a user (`--shard`'s help text, the
  progress group's title, the scoreboard's not-machine-checked line, the C comment
  `gen_inittab.py` writes into the inittab source), the 31 citations in the judge's allowance
  files and the 36 in the guest's own sources (cleared only by a judge change that re-measures
  their fuel). Proposed: *Reserved: NNN (code speaks for itself, the leftovers: the citing
  string literals outside `src/`, held by one regex over string tokens for `spec NNN`; the
  judge's allowance files' comments; the guest's own sources, their fuel re-measured; whether
  a message a user reads falls under the rule is the owner's to say).*

### The builder's self-check

- rebased onto the named stacked base today: re-applied on `d92307f`, the base commit in the
  Status line; the PR branch has not moved since.
- CI run: none of its own, by the chain's rule (the owner, 2026-10-20); the Windows criterion is
  named: the check runs only on macOS and Linux (`own-rest`); it reads files.
- every number from a measured run on this base, labelled EXECUTED; no growth list (no
  artifact byte, no guest fuel: the guest-run sources keep their bytes).
- "For the lane": the claim list, the exact flags, each reason beginning with the spec number,
  the wave kind (parallel-safe by effect, build-class by the letter, a judge change), dry-run
  needs (none of its own).
- every new check seen failing first (2,208 findings on the base's content); no Windows or
  Linux branch in the check (it reads text; `scan.rel`'s `\\` is shared).
- gaps: none; reserved follow-ups: none.
- `packages.toml`: untouched (no package); README rows: none change.
- CHANGELOG: proposed above, not written (the lane's); no owner question raised.
- `ruff check`, `ruff format --check`, mypy, the fast tier: green but for the baseline's 83,
  output in `build/109/`.

### Differences from the specification's text, each with its reason

1. **The base is `d92307f`, not `b7a1250`**, and the chain is 103 to 108, not 102 to 107:
   Decision 7 asked for the re-application on the chain's final tip, and main reserved 102 for
   the release tier on 2026-10-20, so the chain and this file moved up by one (`b42e653`).
2. **The allowance has a third reason**, `SHAPE_SHOWN`, ten rows for
   `tests/checks/test_rules.py`: 107's `src/` citation check, which landed after the first
   build, documents its regexes with the shapes they match (`F3`, `N12`, `F4.2`, …, "memo");
   words cannot show a shape, and the AGENTS.md bullet says the judge reads `context/` as
   data. Decision 5 named two reasons; the count after is 81, not 67, by these 14 hits.
3. **No commit puts the guest's sources back to their bytes**: `clean.py` never edits them and
   `hand.py` skips them, so they never change; their allowance rows went into the allowance
   commit (`1cf9762`) with the `src/` check's rows. The first build's `039cbc4` had both the
   restore and the rows.
4. **Seen failing is one count**, the final check on the base's content, not the first and the
   widened check in turn: the two check commits were rebased whole; the first build's two counts
   stay recorded.
5. **Two sentences were reworded by hand**, batch 17, both 108's: a path to the reviews folder
   in prose became "among the reviews". The rest of the pass is the first build's batches, with
   two olds moved to the chain's text and two stale entries removed (above).
6. **Sameness runs against 108's reviewer record and the chain's baseline**, not 103's built
   record: the chain landed, and the lane's instruction names these two records and the chain's
   claim list.
7. **The four review mentions** of the first build's `cecceed` are made by the batches now, so
   there is no separate commit for them.
