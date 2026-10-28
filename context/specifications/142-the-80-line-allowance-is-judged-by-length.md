# 142: The 80-line allowance is judged by length

- **Status:** **built 2026-10-28** on `spec/142-the-80-line-allowance-is-judged-by-length`, rebased onto `dev` at `0b67fe1b` (144, 145 and 146 merged), its pull request into `dev` open and awaiting its run and its review; drafted 2026-10-27 from the 0.1.1 structural review's one Medium, M-a (`../reviews/0.1.1-structural-review-2026-10-26.md`, finding 1), first stated as M-a of `../reviews/0.1.0-structural-review-2026-10-21.md`; the owner approved what it decides on 2026-10-27, with the 0.1.2 scope (`../roadmap.md`).
- **Date:** 2026-10-27
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**, the judge alone: `tests/harness/scan.py` (`long_function_hits`, about ten lines changed), `tests/checks/test_rules.py` (the values of `LONG_FUNCTIONS`, the comment above it, and the docstring and message of `test_no_function_is_over_eighty_lines`), two rows in `tests/unit/test_scan.py`, the news file, and the roadmap's 142 line in the landing. No file under `src/` changes and no artifact byte moves, so there is no pre-build review: it touches no guest import or export, no part of the artifact set and no build recipe (constitution §5.6), and it adds nothing the structural rule names. It is a judge change with its reason (Decision 5): `test_rules.py` and `scan.py` are judge files but not verdict-bearing (`tests/harness/paths.py:296-304`, READ), so the acceptance records them by the judge's hash and asks no `[claim.judge]` for them (`tests/harness/accept_from.py:286-295`, READ); the news file carries one anyway, for the three lengths this change raises.
- **Depends on:** nothing in flight. Landed and unchanged: 108's function ceiling and its allowance (`108-a-structural-review-is-a-stage.md`, Decisions 5 and 5a), and 138's news files and claim block (`../changes/README.md`). Specifications built beside it that edit a listed function (144 edits `runner.py`'s session paths; 115 and the structural specification of `_instance` and `_open_session` shorten listed functions): whichever lands second measures on its own head after its last rebase, and lists what it measures by Decisions 4 and 5.
- **Research it stands on:** no memo. The two structural reviews: `../reviews/0.1.0-structural-review-2026-10-21.md`, M-a (its line 130, with the EXECUTED failure "with all seven allowances set to 1 line, the scanner returns no hit") and M1(c) (its line 44, whether the ceiling counts docstrings); `../reviews/0.1.1-structural-review-2026-10-26.md`, finding 1 (M-a, carried and grown), L6, and its Verdict ("the structure holds, M-a's closer being 142"). The roadmap's reserved line, `../roadmap.md:108`.

## The problem

108's function ceiling holds every function in `src/wasi_python/` to 80 lines, def to last line, except the functions in its allowance, `LONG_FUNCTIONS` (`tests/checks/test_rules.py:1317-1334`, READ). Each entry carries a length. The check never reads it. `long_function_hits` (`tests/harness/scan.py:2861-2897`, READ) reports an unlisted function past 80 lines, and a listed one that is gone or at 80 lines or under. It never compares a listed function's length with its listed length. The comment above the dict says so in words: "the length beside each key is the record, not the test" (`test_rules.py:1319`, READ).

So a listed function may grow without limit and the check stays green. It has happened twice. Between 0.1.0's bump and its delta read, `run`, `run_async` and `Session.__init__` each grew one line past their listed lengths (the 0.1.0 review, line 130, READ). By 0.1.1 they were five lines past: 156, 181 and 178 against the listed 151, 176 and 173 (the 0.1.1 review, finding 1, EXECUTED there and again here, Decision 6). The cause, as the 0.1.1 review read it, is the three copies of one argument list: 132 added a sentence to each `env` docstring, and 135 one to each `cache_dir` docstring and one `_cache_given` line to each body. Every new argument, or every changed promise about one, adds the same lines three times.

Three documents already rely on the comparison the check does not make: the check's own docstring ("which only shrinks", `test_rules.py:1339`, READ), 108's text ("an entry leaves when its function is at or under 80 lines; none is ever added"), and 114's pre-build review, which told a builder that "the rules check refuses that" (the 0.1.0 review, line 130, READ). The allowance shrinks in name only.

The other direction is open too. Three listed functions are shorter today than listed: `_open_session` 136 against 150, `_instance` 155 against 159, `_Process.__init__` 81 against 82 (Decision 6, EXECUTED). Each gap is slack the next change may spend without a line of the judge moving.

The 0.1.1 review's L6 asked that the roadmap's 115 line count seven functions over 80 lines, not nine. The 0.1.1 preparation pull request made that edit (`6f70f5d5`, whose message names "the roadmap's ... count of functions over 80 lines"; `../roadmap.md:70` now reads "the seven functions over 80 lines", READ at `ee72523e`). L6 needs nothing more here.

## Decisions

### 1. The listed length is the test

`LONG_FUNCTIONS` stays where 108 put it: a dict in `tests/checks/test_rules.py`, keyed `<file name>:<qualname>` (`runner.py:Session.__init__`), each value a whole number of lines. The value becomes the bound. A listed function is green at its listed length and red at any other length. An unlisted function is green at 80 lines or under and red past them. Reason: the dict already has this shape and these keys, so the change is in what the scan reads, not in what the list says; a dict of one number per function is the smallest thing that holds a length, and a raised number shows as a one-line diff in review.

### 2. A length is the scan's existing count

A function's length is what `long_function_hits` counts today: the AST's `end_lineno - lineno + 1` for each `FunctionDef` and `AsyncFunctionDef`, nested ones and methods included under their qualified names. The def line through the last line of the last statement counts, with the docstring, comments and blank lines inside it. Decorators above the def, and comments after the last statement, do not count. Docstrings count, which settles the 0.1.0 review's M1(c): a reader scrolls a docstring as much as a body, and a measure that skipped them would take `run` (51 lines without its docstring), `run_async` (80) and `Session.run_async` (51) off the list without a line of code changing (the 0.1.1 review's measurements row, EXECUTED there). Their repeated argument list is a real cost, and shortening it is 115's work, not a change of measure.

The count is stable because the tree has one form. `ruff format --check` holds `src/` to ruff's formatting in the `quick` job's `ruff` step, which every pull request runs (`.github/workflows/release.yml:157`, READ), with ruff locked at 0.17.1 (`uv.lock`, READ) and a line length of 100 (`pyproject.toml:84`, READ). So a function's length is a function of its code. A ruff upgrade that reformats a listed function moves its length, and that change lists the new length as any other change does (Decisions 4 and 5).

### 3. What the check reports

`long_function_hits` keeps its signature and returns one line per finding, sorted as today. There are five kinds; the two new ones are the second and the fourth.

- An unlisted function past 80 lines, unchanged: `src/wasi_python/runner.py:115: run (156 lines)`.
- A listed function past its listed length: `src/wasi_python/runner.py:115: run (156 lines, listed 151)`.
- A listed function at 80 lines or under, unchanged: `stale allowance: runner.py:run (80 lines)`.
- A listed function shorter than listed and still past 80: `stale allowance: _call.py:_instance (155 lines, listed 159)`.
- A listed function that is gone, unchanged: `stale allowance: runner.py:run (gone)`.

The check passes `what` to `scan.report`, so the failure's first words say what to do: "functions past the ceiling or their listed length (shorten the function, or list the length it has: lower when it shrank, higher only with its reason in the news file's claim)". Reason: the three unchanged forms keep 108's unit rows and anyone's reading of them; the two new ones name both numbers, so the fix is readable from the line alone.

### 4. A listing above its function's length is red, so the list only shrinks

A listed function that shrinks has its listed length lowered by the change that shrinks it. The check is red until it is. A lowered length needs no claim: the shrink is the progress, the diff shows it, and the judge's hash records it. Reason: an allowance that names more than the tree holds is a budget, and the next change spends it unseen, which is the hole this specification closes. The known gaps hold the same rule for the same reason: "a gap is an allowance, not a backlog", and one finding fewer is a different failure that turns the run red (`tests/known_gaps.toml`, lines 1 to 7, READ). With the lower bound red too, each listed number is exactly the function's length on the tree, and the list's sum can only fall unless a change claims a rise.

### 5. A change that must grow a listed function lists the new length and claims it

A specification whose change makes a listed function longer raises that function's value in `LONG_FUNCTIONS` in the same change. Its news file's claim block names `tests/checks/test_rules.py` under `[claim.judge]`, with the reason the function grew (one sentence: what was added, and why it could not go elsewhere). Its Kind line names the function and its new length, as a Kind line names a module's size today. The rise is then seen three times: in the diff of one number, in the claim, and in the Kind line. It is never silent.

The accept job does not refuse a missing claim of this kind, because `test_rules.py` is not verdict-bearing and the job reads `[claim.judge]` for verdict-bearing files alone (`accept_from.py:286-295`, READ). The pull request's review does refuse it: its checklist item 4 reads the news file's claim block against the diff, and "a row changed and not claimed is Medium" (`../reviews/README.md:27`, READ). Reason the list stays in `test_rules.py` instead of moving to a verdict-bearing file: a new data file and its loader, and a path added to `VERDICT_BEARING`, would make every lowered length need a claim as well, for no reader gain; the reviewer already reads every judge diff.

A function not on the list is never added to it, as 108 decided: an unlisted function past 80 lines is fixed in the code. A raise does not by itself make a specification structural: the structural rule names a function taken past 80 lines, and a listed one is already past them; item 4a of the reviewer's checklist still asks whether the change makes a long function worse (`../reviews/README.md:27`, READ).

### 6. The list is reset to the lengths the scan reports

The builder sets each value to what `long_function_hits` reports with an empty allowance on the branch's head after its last rebase onto `dev`, and writes them in the landing notes with the command. At `ee72523e` they are (EXECUTED, `uv run python -c "import sys; sys.path.insert(0,'tests'); from harness import scan, paths; files=[p for p in scan.files_under(paths.REPO,'src') if p.suffix=='.py']; print(*scan.long_function_hits(files, paths.REPO, {}), sep='\n')"`, seven lines), the same seven the 0.1.1 review measured:

| key | listed at `ee72523e` | length at `ee72523e` | moves |
|---|---|---|---|
| `runner.py:run` | 151 | 156 | raised by 5, claimed |
| `runner.py:run_async` | 176 | 181 | raised by 5, claimed |
| `runner.py:Session.__init__` | 173 | 178 | raised by 5, claimed |
| `runner.py:Session.run_async` | 82 | 82 | none |
| `_sessions.py:_open_session` | 150 | 136 | lowered by 14 |
| `_call.py:_instance` | 159 | 155 | lowered by 4 |
| `_process.py:_Process.__init__` | 82 | 81 | lowered by 1 |

The three raises are this specification's own use of Decision 5, with the claim in Design. Reason: the roadmap's line asks for the list "reset to today's lengths", and the rule can only start from what the tree holds; the fifteen lines the entry points gained while nothing judged length are the debt 115 pays, and listing them truthfully is what lets the next line be seen. If a specification built beside this one lands first and moves a listed function, the head's numbers stand in the table's place and the landing notes say which moved and why.

### 7. The check keeps its name

`test_no_function_is_over_eighty_lines` keeps its node id, and its docstring says the new rule: no function past 80 lines unless listed, and no listed function at any length but its listed one. Reason: a renamed check is an accepted check gone absent and a new one, which the acceptance must retire by a claim, for a name that still says what the check is for.

### 8. The rows first

- `tests/unit/test_scan.py`, a new row `test_a_listed_function_past_its_length_is_a_hit`: an 82-line `f` listed at 81 gives `["m.py:1: f (82 lines, listed 81)"]`; the same `f` listed at 82 gives `[]`. Red today: the scan returns `[]` for the first (EXECUTED on `ee72523e`).
- `tests/unit/test_scan.py`, a new row `test_a_listed_function_shorter_than_its_length_is_a_stale_allowance`: an 81-line `f` listed at 83 gives `["stale allowance: m.py:f (81 lines, listed 83)"]`. Red today: the scan returns `[]` (EXECUTED on `ee72523e`).
- An unlisted function past 80 lines is a hit today and stays one: `test_a_function_over_the_ceiling_is_a_hit` (`tests/unit/test_scan.py:390`, READ) already holds it (an 81-line `f`, unlisted, gives `m.py:1: f (81 lines)`, EXECUTED), and its other assertions list each function at its exact length, so it stays green unchanged. It is the regression row for the unchanged forms, not a red-first row.
- The rules check itself: with the new scan and `LONG_FUNCTIONS` at `ee72523e`'s values, `test_no_function_is_over_eighty_lines` fails with six findings, three past their listed length and three stale; with the reset values it passes. Both runs are named in the pull request.

## Intent

After this specification, the long-function allowance means what its comment has always said: each listed function is held at the length it has, it can only get shorter unless a change says in writing why it grew, and a shorter function lowers its own listing in the change that shortens it. A reviewer who reads `LONG_FUNCTIONS` reads the tree's exact debt of long functions, and a change that adds to it is seen.

In one line: a listed function is judged by its length, not only its name.

## Design

- `tests/harness/scan.py`, `long_function_hits`: after the walk, for each allowed key, gone is `stale allowance: key (gone)` as today; at or under the ceiling is `stale allowance: key (n lines)` as today; under its listed length and over the ceiling is `stale allowance: key (n lines, listed m)`; over its listed length is `rel:line: qualname (n lines, listed m)`, which needs the walk to keep each key's path and line beside its length. The section comment above it and its docstring say the listed length is the bound (Decision 1).
- `tests/checks/test_rules.py`: the comment above `LONG_FUNCTIONS` says the length beside each key is the test, that a shrink lowers it in the same change, that a rise is claimed in the news file, and that no key is ever added; the seven values become Decision 6's; the two comments inside the dict, which give each group's reason in words, stay; the check's docstring says the rule (Decision 7) and its `scan.report` call passes Decision 3's `what`.
- `tests/unit/test_scan.py`: the two rows of Decision 8, next to `test_a_function_over_the_ceiling_is_a_hit`, using its `_function` helper (`tests/unit/test_scan.py:384`, READ).
- The news file `../changes/142-the-80-line-allowance-is-judged-by-length.md`, with no package rows, its changelog under Changed: "The 80-line allowance is judged by length: each function the long-function allowance lists is held at its listed length, one that grows past it or shrinks below it is reported, and the list is reset to the lengths the tree has (`run` 156, `run_async` 181 and `Session.__init__` 178 lines, which had grown past their listings unseen)." Its claim block:

```toml
[[claim]]
spec = "142"
units = 2
[claim.judge]
"tests/checks/test_rules.py" = "the long-function allowance's lengths become the bound; run, run_async and Session.__init__ are listed at 156, 181 and 178, the lengths they reached while nothing judged a length (the three entry points repeat one argument list, which gained a sentence for env and one for cache_dir in each docstring and one line in each body); _open_session, _instance and _Process.__init__ are lowered to 136, 155 and 81"
```

- `../roadmap.md`: in the landing, the 142 line becomes a landed line in the house form (pull request, review file, acceptance), as line 82 is for 131. No edit for L6, which the 0.1.1 preparation made (The problem).
- The commits, in order: the two unit rows, seen failing; the scan; the reset of `LONG_FUNCTIONS` with the check's docstring and message (the rules check seen failing between the two); the news file; the review file last.

## Scope

In: the above. Out:

- Shortening any function, including the shared argument list of the three entry points' docstrings that the 0.1.1 review's M-a asks folded in (the 0.1.0 review's M1(c)): that changes `src/`, and it is 115's, whose roadmap line names the seven functions (`../roadmap.md:70`, READ).
- The duplication of `_instance` and `_open_session`: the structural specification of its own that `../roadmap.md` names after 142.
- The seam allowance, `SEAM_ALLOWED`: 115.
- A different measure of length (statements, complexity, or lines without docstrings): Decision 2 keeps the scan's count.
- Making `tests/checks/test_rules.py` verdict-bearing, or moving the allowance to a file that is: Decision 5 says why not.

## Acceptance criteria

1. The two new rows of Decision 8 exist in `tests/unit/test_scan.py` and were seen failing on the base, each named in the pull request with its failing output; `test_a_function_over_the_ceiling_is_a_hit` is unchanged and green.
2. With the new scan and the old values, `test_no_function_is_over_eighty_lines` failed with six findings (three `listed` hits, three `stale allowance` lines), named in the pull request; with the reset values it passes.
3. `LONG_FUNCTIONS` holds the same seven keys, each value equal to the length the scan reports on the pull request's head (Decision 6), and the landing notes give them with the command, labelled EXECUTED.
4. `git diff --stat dev...HEAD -- src/` is empty: no function moved.
5. The news file exists with its line under Changed and its claim block, and `tests/checks/test_rules.py::test_the_news_files_have_their_shape` passes.
6. The pull request's run: `quick` green with its `lint` step (`uv run pytest tests/lint`), the fast tier loses no accepted pass, and `ci-status` is green.

## Landing notes

Built 2026-10-28 by an agent (Claude Opus 5.5), the one that drafted the specification, in the worktree `../wasi_python-wt/spec-142`. Not yet landed: the pull request's run, its review and the merge are to come, and 147 and 143 may still move a listed length before the merge, in which case the builder re-measures once more and these notes change with it.

**The commits.** The specification; the two unit rows, seen failing; the scan; the reset of `LONG_FUNCTIONS` with the check's docstring and message (the rules check seen failing between the two); the news file; and, after the rebase onto `0b67fe1b`, the head's lengths with these notes.

**Seen failing first** (EXECUTED on `ee72523e`, each output kept under `build/142/`, not committed):

- `test_a_listed_function_past_its_length_is_a_hit`: `AssertionError: assert [] == ['m.py:1: f (82 lines, listed 81)']`.
- `test_a_listed_function_shorter_than_its_length_is_a_stale_allowance`: `AssertionError: assert [] == ['stale allowance: m.py:f (81 lines, listed 83)']`.
- `test_no_function_is_over_eighty_lines`, with the new scan and the old values: `6 finding(s), digest 3092c2796d92`, the three entry points past their listed lengths (156 against 151, 181 against 176, 178 against 173) and three stale listings (`_open_session` 136 against 150, `_instance` 155 against 159, `_Process.__init__` 81 against 82). With the reset values it passed.

**The lengths on the head** (EXECUTED on the branch rebased onto `0b67fe1b`, `uv run python -c "import sys; sys.path.insert(0,'tests'); from harness import scan, paths; files=[p for p in scan.files_under(paths.REPO,'src') if p.suffix=='.py']; print(*scan.long_function_hits(files, paths.REPO, {}), sep='\n')"`, seven lines): `runner.py:run` 156, `runner.py:run_async` 181, `runner.py:Session.__init__` 178, `runner.py:Session.run_async` 81, `_sessions.py:_open_session` 138, `_call.py:_instance` 155, `_process.py:_Process.__init__` 83. `LONG_FUNCTIONS` holds exactly these.

**What moved since Decision 6's table**, measured by the same scan on an export of `src/` at each merge (EXECUTED): 145 (`658a6213`) moved none; 146 (`2a13298b`) took `_Process.__init__` from 81 to 82 (the abandoned tool threads' count) and `_open_session` from 136 to 138 (the tool host's abandoned count and its wait bound, two arguments); 144 (`0b67fe1b`) took `_Process.__init__` to 83 (`pool_done`, the queue of pools whose futures are done) and `Session.run_async` from 82 to 81. Against the listing at `ee72523e`, four lengths rise (`run`, `run_async`, `Session.__init__` by 5 each, `_Process.__init__` 82 to 83) and three fall (`Session.run_async` 82 to 81, `_open_session` 150 to 138, `_instance` 159 to 155). The news file's claim names each rise with its reason, and its CHANGELOG line names the four that had grown unseen.

**Verification on the head** (EXECUTED, `WASI_PYTHON_ARTIFACTS` set to the 0.1.1 set): `uv run ruff check src tests` and `uv run ruff format --check src tests` clean; `uv run pytest tests/unit/test_scan.py -q` all passed; `uv run pytest tests/checks/test_rules.py -q -p no:cacheprovider` exit 0; `uv run pytest tests/lint -q -p no:cacheprovider` all passed. The counts are in the pull request's description.

**One difference from the Design's text.** Design says the walk keeps each key's path and line beside its length for a later pass. The scan reports a grown listed function inside the walk instead, as `elif n > FUNCTION_CEILING and n > allowed[key]` after the unlisted branch. The output and its sort order are the same, and a listed function at 80 lines or under is still reported as a stale allowance, not as grown. Reason: one branch where the line and qualified name are already at hand, instead of a second map.

**No gap added**: `tests/known_gaps.toml` is unchanged. No file under `src/` changes (`git diff --stat origin/dev...HEAD -- src/` is empty, EXECUTED).
