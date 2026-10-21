# Review of 108 — A structural review is a stage (build)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent; not the author of the build nor of the specification
- **Reviewed:** `0e145b7..3dc9f1f` on `spec/108-a-structural-review-is-a-stage` in
  `/home/user/wt/108` (six commits; `0e145b7` is the PR branch `claude/gallant-ride-9nxxmn`'s
  tip, 107's reviewed and landed tip: EXECUTED, `git rev-parse`). Seven files, `src/` and
  `tests/public_api.txt` untouched (EXECUTED, `git diff --stat 0e145b7 3dc9f1f -- src
  tests/public_api.txt` empty); `release/` untouched (the factored loader lives in
  `tests/checks/test_rules.py`).
- **Run:** none of its own, by the chain's rule (the owner, 2026-10-20): the chain dispatches
  the release workflow once on its final tip, which this specification's tip is unless 109 is
  re-applied after it; that run's id is the lane's to write here. The fast tier below is this
  review's re-run of the counted tests.
- **Re-ran:** (all EXECUTED on `3dc9f1f`, the worktree clean, the frozen `v0.1.0a7` set,
  `WASI_PYTHON_ARTIFACTS=/home/user/wasi_python/build/baseline-a7/set/wasi-python-0.1.0a7`)
  - `uv run pytest -m "not slow" -n 3 -q -p no:cacheprovider` under
    `build/fast-tier.lock`, `SIGINT` at its default through `build/108/with-sigint.py` →
    **83 failed, 2440 passed, 52 skipped in 277.86s**, exit 1; the 83 are exactly
    `build/baseline-a7/failing-nodes.txt` (`diff` of the sorted lists empty,
    `build/108/review-failed-nodes.txt`). Record: `build/108/review.json` (`review-fast.log`).
  - `uv run python tests/harness/sameness.py /home/user/wt/107/build/107/review.json
    build/108/review.json --claims build/108/claims.toml` → `note: explained by claims: 108 5`,
    exit 0 (`build/108/review-sameness-107.txt`).
  - `uv run python tests/harness/sameness.py /home/user/wasi_python/build/baseline-a7/baseline.json
    build/108/review.json --claims build/108/claims-chain.toml` → `note: explained by claims:
    103 4 · 104 3 · 105 4 · 106 3 · 107 4 · 108 5`, exit 0
    (`build/108/review-sameness-baseline-chain.txt`).
  - `uv run pytest tests/checks/test_rules.py -q -p no:cacheprovider` → 1 failed, 53 passed,
    3 skipped; the one failure is `test_version_states_the_platform_semantics`, the older a7
    set's, in the baseline's 83 (the builder's "53 passed, 4 skipped" is the same file run
    without the artifact set, where that check skips).
  - `uv run pytest tests/unit/test_scan.py -q -p no:cacheprovider` → 215 passed.
  - The four new nodes by id → 4 passed in 1.49 s; the seam check takes 1.14 s (it parses every
    string constant under `tests/`), the ceiling 0.18 s.
  - `uv run ruff check src tests release` → All checks passed; `uv run ruff format --check src
    tests release` → 147 files already formatted; `uv run mypy --strict src/wasi_python` →
    Success, 18 source files; `uv run python tests/harness/api.py --check` → exit 0, no output.
  - `uv run python release/version.py check` → `ok 0.1.0a8` on the tip and on the base
    (`/home/user/wt/107`, `0e145b7`): `release/` behaves as before.
- **Box:** 60 minutes (the lane's, for a judge-and-context specification that changes the
  review stage); the whole checklist was worked, with 4a and the structural rubric read for
  whether they apply.

## The builder's self-check

Read in the landing notes ("The builder's self-check"). Every item is present: the stacked base
in the Status line; CI named as none of its own by the chain's rule, the Windows criterion
named (`own-rest`, macOS and Linux: `tests/release_shards.toml:78–79`, READ); numbers EXECUTED
with commands; the claim list, flags, kind and dry-run needs; every check seen failing first
(`build/108/seen-failing-*.txt`, READ); the four seams for the integration review as the
reserved follow-up; `packages.toml` and README untouched; the CHANGELOG line proposed, the
question numbered 108 from 107; ruff and the fast tier green but for the baseline's failures.
One item is met only in part (finding 1): "every reserved follow-up has a roadmap line" holds
for the four names handed to the integration review, not for the rest of the two allowances.

## Acceptance criteria against evidence

1. **The texts are in the tree, verbatim** — met. The six fenced blocks of Design A to C, read
   from the specification's own fences by a scratch script
   (`/tmp/claude-0/-home-user-wasi-python/a7a0f302-7717-538b-8fac-46c5fd7843f5/scratchpad/verbatim.py`):
   A1 (17 lines) and A2's new text (3 lines) present in `AGENTS.md`, A2's old text absent; B1
   (5 lines) and B2 (117 lines) present in `context/reviews/README.md`; C (37 lines) present in
   `context/questions-for-the-owner.md`, under "## Open", "None." gone (EXECUTED). The
   question's shape (`### 108. …`, then **Asked**, **The fact**, **The question**, the
   amendment, the Status entry, the recommendation, **Meanwhile**) is the shape of the answered
   questions in `decisions.md` (READ, `decisions.md:309`, `:572`). Its heading carries no
   "question", and the open-question scan reads specifications, `README.md` and `AGENTS.md`,
   not the owner's file (`tests/checks/test_rules.py:153–156`, READ); AGENTS.md's new bullet
   passes it (criterion 8). A1 sits after "Nothing lands unreviewed" and before "Code speaks
   for itself", the bullet the owner added on 2026-10-20 between the two the Design names:
   acceptable, since Decision 1 asks for "right after Nothing lands unreviewed" as the
   structural twin of that bullet and the later bullet is the owner's. `decisions.md` untouched
   (the diff lists seven files: READ). E1 to E3 are proposed in the landing notes, not written,
   as 103 to 107 did; the roadmap and CHANGELOG are the lane's at the wave (READ).
2. **Check (a), seen failing first** — met. `scan.structural_review_errors("0.1.0",
   context/reviews)` on this tree → `['0.1.0 is a release; reviews/ has no
   0.1.0-structural-review-<date>.md']`; `"0.1.0a8"` → `[]`; `"0.1.0rc1"` → `[]`; `"1.0.0"` →
   the one error (EXECUTED, `build/108/probes/counts.py`). `read_version` of
   `src/wasi_python/__init__.py:53` gives `0.1.0a8`, so the check passes on the tree (EXECUTED,
   the node by id). The `AttributeError` on the base: `seen-failing-review-checks.txt` (READ).
3. **Check (b), seen failing first** — met. The unit row's `112-c.md` case passes (EXECUTED,
   `test_scan.py`); `seen-failing-structural-spec.txt` records the check naming this file with
   the token and no citation (READ). On the tree the Kind lines of 103 to 107 carry
   `**parallel-safe**`, none `**structural**` (EXECUTED, `grep -A3 '^- \*\*Kind:\*\*'`), and
   108's own carries neither word nor token; so the check holds nothing of the chain today, as
   Decision 4b intends (103 to 107 were reviewed before build under rule 8's "the runner's
   code"; their builders may add the token at the wave). It binds from the next structural
   specification on.
4. **The seam check, seen failing first** — met. `scan.seam_hits` over every `.py` under
   `tests/` with the allowance empty → **36 sites, 18 names**, the builder's list name for name
   and count for count (EXECUTED, `counts.py`); the 107 "for 108" list agrees but
   `_sessions._Phase`, which is a parameter annotation at `test_runner_sessions.py:104`, not a
   patch (EXECUTED, `sed -n 104p`). `SEAM_ALLOWED` is those eighteen; a stale entry is red
   (`seen-failing-seams-stale.txt`, READ; the unit row's `stale allowance: _x`, EXECUTED).
   Probes of forms the builder did not list are under "Probes" below.
5. **The function ceiling, seen failing first** — met. `scan.long_function_hits` over `src/`
   with the allowance empty → the nine of `LONG_FUNCTIONS` with the recorded lengths
   (EXECUTED, `counts.py`). By hand: `runner.py:run` is `def run(` at line 115 and its last
   line 265, 151 lines; `_process.py:_Process.__init__` 97 to 178, 82 lines (EXECUTED,
   `sed -n`). The rule is `end_lineno - lineno + 1`: docstring, blank lines and nested bodies
   count, decorators do not, a nested function counts again on its own under `outer.inner`
   (READ, `scan.py`; the unit row's `f` 83 and `f.g` 81, EXECUTED). At exactly
   `FUNCTION_CEILING` silent, at `+1` a hit (the unit row, EXECUTED). A key is
   `<file>:<qualname>`, so a renamed or moved function reads `stale allowance: … (gone)` and
   a shortened one `stale allowance: … (n lines)` (EXECUTED, the unit row's `m.py:h (gone)`;
   `seen-failing-long-functions-stale.txt`, READ). The README's one-liner on the tip gives
   `_call.py 1, _process.py 1, _sessions.py 1, runner.py 4, tools.py 2` = 9 (EXECUTED).
6. **The unit rows pass, each seen failing first** — met: `test_scan.py` 215 passed (EXECUTED);
   ruff clean (EXECUTED); the base's `AttributeError` records (READ).
7. **No verdict moves** — met: both sameness outputs above, exit 0, only the claims' note
   (EXECUTED); the 83 failures are the baseline's exactly (EXECUTED).
8. **The open-question scan is green** — met: in `test_rules.py`'s 53 passed (EXECUTED).
9. **Nothing under `src/` changed** — met (EXECUTED, above); `api.py --check` exit 0; mypy 0.
10. **The release workflow: no dispatch of its own** — met by the chain's rule; the Run line
    says whose run it is (READ).

## Probes (checklist item 5; the lane's point 1)

A scratch file `build/108/probes/t/test_p1.py` (git-ignored, not under `tests/`) with eleven
forms, run through `scan.seam_hits` with an empty allowance (EXECUTED,
`build/108/probes/run_probe.py`):

| form | seen |
|---|---|
| `with monkeypatch.context() as m: m.setattr(h, "_stack", 1)` (`import wasi_python._home as h`) | hit, `_home._stack` |
| `h._stack = 1` (the alias) | hit |
| `wasi_python._home._stack = 1` (the full path, after `import wasi_python`) | hit |
| an f-string program `f"import wasi_python.runner\nwasi_python.runner._x = {1}\n"` | hit, `runner._x` |
| a program in two constants, `"from wasi_python import _call\n" + "_call._drive = 1\n"` | hit |
| `monkeypatch.setattr(_call, "_epoch_now", 1, raising=False)` | hit |
| a `.format` template `"import wasi_python._home\nwasi_python._home._stack = {value}\n"` | hit |
| `mock.patch.object(h, "_stack", 1)` | **missed** |
| `mock.patch("wasi_python._call._drive", 1)` | **missed** |
| the builtin `setattr(runner, "_current_defaults", 1)` | **missed** |
| `monkeypatch.setattr(target=_call, name="_stop_error", value=1)` (keywords) | **missed** |
| a string that does not parse, holding its own `from wasi_python import _sessions` and `_sessions._abandon_turn = 1` | **missed** (the regex fallback reads the file's imports, not the string's) |

The tree uses none of the missed forms: `grep -rnE "mock\.patch|patch\.object|from unittest
import mock|\bpatch\("`, the builtin-`setattr` grep and the keyword grep over `tests/` each find
nothing (EXECUTED); the two `monkeypatch.delattr` sites (`test_wasmtime_ffi.py:135, 137`) are on
`wasmtime._ffi` and the package, outside the rule. So the misses are a Note (finding 2), not a
finding. A second probe (`test_p2.py`): a prose docstring saying "set runner._x = 1 here" is a
hit, and so is one in backticks (the string does not parse, the regex sees it): the check is
conservative, a red that is visible and fixed by wording (finding 3).

## Findings, most severe first

1. **The two allowances have design closers but no numbered closer** (`tests/checks/test_rules.py`,
   `SEAM_ALLOWED` and `LONG_FUNCTIONS`; the landing notes, "For the integration review") — Low.
   Each group's comment says what closes it (fields of the home, parameters of the remover, rows
   of the lifecycle table, a shared argument object), which is what "Code speaks for itself"
   allows a code file to say. But the specification's closers were "107's platform seam, 107's
   call-context protocol, 106's typed call" (Decision 5a), 106 and 107 have landed, and fourteen
   of the eighteen names and all nine functions outlive them; the notes hand only the four names
   outside the twenty-four to the integration review, and `context/roadmap.md` carries no line for
   the rest (EXECUTED, `grep -in 'seam\|SEAM_ALLOWED\|LONG_FUNCTIONS\|80 lines' context/roadmap.md`
   finds only 109's paragraph). The lists "only shrink", so nothing is lost, but the self-check's
   "every reserved follow-up has a roadmap line" is met only for the four.
   Failure: no specification is reserved → the eighteen seams and nine long functions stay as
   they are through 0.1.0, and the first structural review scores R6 and R7 against a list
   nobody owns.
   Fix text, for the lane's roadmap commit at the wave (the roadmap is the lane's; touches only
   `context/`), one paragraph after E1's "Reserved: 108" paragraph: "Reserved: a closer for
   spec 108's two allowances (the eighteen private runner names the judge still patches,
   `SEAM_ALLOWED` in `tests/checks/test_rules.py`, each with the field or parameter its comment
   names; the nine functions over 80 lines, `LONG_FUNCTIONS`): parallel-safe, `src/` and the
   tests that patch, one specification or two; before the first structural review scores R6
   and R7, or named in that review as the Medium's reserved specification." No round needed.
2. **The seam walk does not see `unittest.mock`, the builtin `setattr`, keyword arguments or a
   non-parsing string's own imports** (`tests/harness/scan.py`, `_seam_sites`,
   `_seam_sites_in_text`) — Note. The probes above; the tree uses none of these forms
   (EXECUTED). The walk sees every form the tree holds, two more than the Design listed, each
   with a unit case. Disposition: none now. The specification that next touches the scanner, or
   the first that reaches for `mock.patch`, adds the form and its unit row; the rules' comment
   already says the one way is through `process()`.
3. **A docstring that mentions `runner._x = 1` in prose is a hit** (`scan.py`,
   `_seam_sites_in_text`'s regex fallback) — Note. Conservative: the red names its line and the
   fix is wording. None on the tree (the check is green). No disposition needed.
4. **`test_rules.py` alone under the frozen set reads 1 failed** — Note, for the next reader.
   The failure is the a7 set's `test_version_states_the_platform_semantics`, in the baseline's
   83; the builder's "53 passed, 4 skipped" is the file without the artifact set. The counts
   agree on the 53.

## Constitution checks

- §4 constraints: §4.1 (upstream patches) untouched; §4.10 (every number with its command,
  labelled) holds, the landing notes' numbers re-measured above and found equal; §4.14 (one
  specification per branch, stacked on a reviewed tip) holds, the base `0e145b7` is 107's landed
  tip (EXECUTED). "Code speaks for itself": the added judge code names no specification, memo,
  review, finding ID or `context/` path (EXECUTED, a grep over the diff's added lines: every
  "review" is the subject the checks read as data, `context/reviews/`, which the AGENTS.md bullet
  allows the judge to read; the one `(spec 004)` is a pre-existing docstring's line moved by the
  factoring, 109's to clear). "Never weaken the judge": no check, golden, gap, allowance or
  progress file is edited; the two new allowances record the tree and only shrink; the judge
  hash changes in the three files the claim list names.
- §7 never-do list: nothing tripped. No `--accept`; no build; no slow tier; no artifact byte.
- Checklist 4a (structure, one line): the diff touches no file under `src/`; it adds no concern,
  flag, mutable, seam, platform branch, private-API use or long function; no row moves, and the
  Kind line rightly carries no `**structural**`. The README's "Structural review" section applies
  to a release review and to a structural specification; this is neither, so the eight rows are
  not scored here (the branch's README, READ).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 (Low, context only) — the fix text is for the lane's roadmap commit at the wave;
   no round.
2. Findings 2 to 4 (Notes) — no action.

## Verdict

Lands: every criterion is met with its evidence, the two allowances are the tree's as measured,
no verdict moves, and the one Low is a roadmap line for the lane.
