# Review of 049 — The public API is frozen and documented (the build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the specification, its pre-build review, its confirmation or the build. I read `AGENTS.md`, the constitution (§4, §5.6, §7), `context/reviews/README.md`, `context/progress/README.md`, specification 049 in the worktree in full (the status line with C1 and C2, Decision 8 as revised for question 88, the landing notes and the builder's "where the specification was silent" list), its pre-build review `049-the-public-api-is-frozen-spec-2026-10-18.md` with the Disposition and the Confirmation, and 034's build review for the form. I read the whole diff `1c0123c...HEAD`: `__init__.py`, `runner.py`, `tools.py`, the non-docstring lines of `mounts.py`, `tests/harness/api.py` in full, `tests/checks/test_v1_4_public_api.py` in full, `tests/public_api.txt` in full, the README outside the generated block and samples of the block, the CHANGELOG, `context/README.md`, and the renamed judge lines. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** commits `6f7a2fe`, `259fc0a`, `85547a4`, `48a9f88`, `e700ce8`, `9e0bc0c` on `spec/049-the-public-api-is-frozen`, worktree `../wasi_python-049`, from `1c0123c`. Files as reviewed (SHA-256 prefix, EXECUTED): `__init__.py` `a2ac14f2c111`, `runner.py` `22695ca8c1c7`, `tools.py` `7b62dab4a1be`, `tests/harness/api.py` `85098ac667b8`, `tests/public_api.txt` `b48883c5ebe0`.
- **Re-ran (EXECUTED, darwin-arm64, `uv run` only, nothing committed, nothing tracked edited).** Scripts and outputs beside this file, in `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/049-buildreview/`:
  - `judge.log`: `WASI_PYTHON_ARTIFACTS=<main>/build/sets/s-f94dec535086b06c uv run pytest`, no flags, once, in the worktree → exit 0: `wasi_python v1: 275/286 pass · 0 gap · 11 blocked · 0 fail (unit suite 934/942, 8 skipped)`; v1.4 135/135; `ratchet vs 01238501f8: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 10 · grew 0 · judge changed: tests/checks/test_v1_4_public_api.py, tests/harness/api.py, tests/harness/artifacts.py and 7 more`; `1209 passed, 19 skipped`. The same lines the landing notes quote.
  - `uv run ruff check src tests` → all passed; `uv run ruff format --check src tests` → clean.
  - `tests/harness/api.py --check` on 3.11.14, 3.12.12, 3.13.11 (`uv run --no-project --offline --python 3.1x`) and the dev 3.14.2 → exit 0 on each.
  - `mutate.py` → `mutate.log`: 21 mutations of a `git archive HEAD` copy (`base/`), each checked with `api.py --check --package <copy>` and the rule functions of criteria 3 to 6; plus `mut/cli2` (a clean option rename), `mut/lock` and `mut/direct` (criterion 10 run with `PYTHONPATH=<copy>/src` against two runner mutants, and a control).
  - `merged/`: `git merge-tree` of the branch onto main `28800bc` (050 landed) is clean (`d8f208c`); `api.py --check` on that tree exits 0 and the README rule finds 0 hits.

## Acceptance criteria against evidence

1. Snapshot matches — **met.** The check passes in the judge (EXECUTED). Mutations: renaming `artifact_dir`, adding a keyword-only `extra: int` to `run`, adding an `Errno` member, changing a default, unfreezing `Grant`, swapping `Grant`'s fields, bumping `PROTOCOL`, rebasing `ToolDenied` on `Exception`, adding a `stats()` key, renaming a CLI option, and renaming the `run` subcommand each make `--check` exit 1 with the expected snapshot lines (EXECUTED, `mutate.log`). One promise the snapshot does not see: F5.
2. Exactly their `__all__` — **met.** 20 and 9 names; `import *` binds exactly them (EXECUTED, judge).
3. Underscore rule — **met.** 0 names. A mutant `HELPER = 2` in `tools.py` is reported as `wasi_python.tools.HELPER (assign)` (EXECUTED).
4. Nothing private re-exported — **met**, with its stand-in (EXECUTED, judge).
5. Documented — **met.** Every count 0. Dropping `defaults()`'s docstring, adding an undocumented `Tool.extra`, an undocumented parameter, a `(spec 017)` in `Grant`'s docstring, a missing `KeyboardInterrupt` in `run`'s `Raises:`, and a `stdin` text that differs between `run` and `run_async` are each counted (EXECUTED, `mutate.log`).
6. Nothing internal named — **met.** 0 and 0; C1's stand-ins give (6, 0, 3), the indented fence case and the fenced hit (EXECUTED, judge). Mutants: `` `CANCEL_TICKS` `` and `` `wasi_python.runner.DEFAULTS` `` in README prose and `` `BASE_ENV` `` in `run`'s docstring are each one hit (EXECUTED).
7. Annotations resolve — **met.** 171 evaluated, 0 failed; the two overloads' shapes as specified, and their keywords equal the implementation's (EXECUTED, judge; READ).
8. Typed — **met.** `py.typed` tracked; the wheel rule and its stand-in pass (EXECUTED, judge). The built wheel's content is the builder's claim (not re-run).
9. README reference — **met** (EXECUTED, judge); every snapshot mutation above also changed the block (EXECUTED).
10. `set_defaults` — **met as written**, but the check is weaker than its text: F2.
11. Same render on 3.11 to 3.14 — **met** (EXECUTED, above).
12. Update path — **met**: my `extra: int` mutant gave one snapshot line, one signature line and one empty `Args` entry in the block, and an `Args entries` gap (EXECUTED). `--write` itself was not re-run by me.
13. Existing checks green, ruff clean, lost 0, grew 0 — **met** (EXECUTED, above). Acceptance with `--accept-judge` is the lane's.

034's checklist (Decision 13) — **every item appears exactly** (READ, `tests/public_api.txt`): `RefusedWrite`'s six fields in order; `WritableFileProvider(FileProvider)` with `write`, `mkdir`, `remove`, `rmdir`, `rename`; `Mount.writable: bool = False kw_only`; `FileRecord.refused` and `refused_total` last; 20 names.

## Findings, most severe first

1. **The README's promise drops "whose default keeps today's behaviour"** (`README.md:1220` and `1225`, the hand-written paragraph) — Decision 8 lets a minor release add "keyword-only arguments whose default keeps today's behaviour"; the README, which Decision 8 names as where the promise lives, says only "keyword-only arguments". **Low-medium.** Failure: 0.2.0 adds `run(..., strict: bool)` with no default, or one whose default changes behaviour; the README's own words allow it, every existing call breaks, and the spec and the README disagree on which governs. Fix: add the phrase (and "or keyword-only" for fields). The same paragraph says the judge fails on any change "that no specification lists"; the judge fails on any change not regenerated, and the listing is a review rule. Say "until it is regenerated, which a specification must list".

2. **Criterion 10 cannot see a second read of the defaults, nor the old value read outside the lock** (`tests/checks/test_v1_4_public_api.py:303-356`) — it counts calls to `_current_defaults`, and its lock stand-in records `DEFAULTS` on enter and exit. **Low.** Failure, both EXECUTED on copies: (a) `_check_places` changed back to `DEFAULTS.file_calls` reads the defaults twice per call, and criterion 10 passes (`mut/direct`); (b) `old = _runner.DEFAULTS` moved above `with _defaults_lock:` reopens F7's lost restore, and criterion 10 passes (`mut/lock`; the control with the lock removed fails, so the copy was the one tested). This matters most at the rebase on 056 (below), where `_check_tools` may be touched. Fix, in the check: by `ast`, `runner.py` loads the name `DEFAULTS` only inside `_current_defaults`; and the lock stand-in's `__enter__` sets `runner.DEFAULTS` to a sentinel, so `set_defaults` must return the sentinel. The code as built is right on both counts (READ, `__init__.py:160-163`, and every `DEFAULTS` load in `runner.py`, EXECUTED by `grep`).

3. **A stale `async_workers` can now resize the pool back** (`runner.py:555`, `_submit`) — before this change `_submit` read `DEFAULTS.async_workers` under `_pool_lock`, so the newest value always won; now each call carries the size it read in `_checked`, and the pool is replaced whenever a call's size differs. **Low.** Failure (INFERRED from the code; not run): thread A calls `run_async` and reads 8, then spends its first call importing wasmtime-py in `_wasmtime()`; thread B calls `set_defaults(... 4)` and `run_async`, which makes a 4-pool and leaves the 8-pool draining; A then submits with 8 and makes a third pool; B's next call makes a fourth. More than the "up to 12 at once" that `set_defaults`' docstring and the README's new sentence state can run, and the 8.3 GiB bound is briefly exceeded. Decision 2 asked for exactly this wiring, so it is a spec-and-build finding. Fix, either: the pool size is process state, not a per-call limit, so `_submit` reads `_current_defaults().async_workers` under `_pool_lock` (exempt it from "one read per call" in Decision 2, in a sentence); or keep the wiring and soften "up to 12" to "more than either size, briefly". Answer in writing is acceptable.

4. **Two of the builder's rules bind later specifications but live only in the landing notes** (spec, "Where the specification was silent") — "a constant is documented by being named in backticks in its module's docstring" and "names unpacked together, dunders and `Errno`'s members are not internal names" are rules `api.py` enforces; Decision 13 sends later drafters to Decision 10, which does not state them. **Low.** Failure: the next specification adds a public constant, gives it a `#` comment, and meets a failing "named in no module docstring" with no rule to read. Fix: one sentence each in Decision 10. The other choices are right and need nothing more (my judgement on each: PROTOCOL in the module docstring, yes, a constant has no `__doc__`; dunders exempt, yes, as Decision 4 says; the entry point left out of the README block and kept in the snapshot, yes, it names `wasi_python.cli` and a user runs the command, not the target; criterion 10 with `tools=`, yes, without tools `_check_tools` returns before its read, so the three-read stand-in would count 2; the seen-failing counts, yes, explained, and the step-2 counts match the spec's plus 034's).

5. **`Tool`'s identity equality is promised in its docstring but not in the snapshot** (`api.py:_class`, `tools.py:125`) — the render records `frozen` only, not `eq`, `order` or `unsafe_hash`. **Low.** Failure (EXECUTED, `mutate.log`, "Tool eq=True"): `@dataclass(frozen=True)` on `Tool` makes two tools with equal fields compare equal and hash by value, a behaviour change a user's set or dict of tools would see, and `--check` exits 0. Fix: render the dataclass parameters that differ from the defaults (`eq=False`), or accept in writing that equality is not in the snapshot.

6. **Stale text in the specification** (spec, Status line; Decision 13; Design table) — the status line still carries "awaiting the reviewer's confirmation" from the revision, and Decision 13 and the Design table still say the lane applies the `context/README.md` sentence, which C2 moved into the branch (it is there, READ). **Nit.** Fix: make the body agree with C2.

Notes, no change asked:
- **README growth.** 1,413 to 2,146 lines (EXECUTED, `wc -l`); the block is lines 1239-1942, 703 lines, about twice the pre-build estimate, mostly the 19 `run` arguments and the `tool` overloads in full. Decision 11 put it in the README on purpose, and it is generated, so it cannot drift. Acceptable. If the README keeps growing, a generated `docs/api.md` linked from the README is a one-line change to `api.py`'s `--readme` default; that is a later spec's call. The block's `async_workers: int = <factory>` is not valid Python in a `python` fence, and the command table gives argparse action names, not what each option does; both cosmetic.
- **`api.py` reads argparse internals** (`parser._registry_get`, `parser._actions`). It works on 3.11 to 3.14 (EXECUTED). A future CPython that changes them fails the render loudly, not silently, since an unknown action raises.
- **The renames before 0.1.0** are allowed (Decision 8: alphas may change anything) and are in the CHANGELOG under Changed with the reason (READ). No file in `scripts/`, `.github/` or `recipes/` on main `28800bc` names the old names (EXECUTED, `git grep`); `runner.DEFAULTS` users remain only in the judge, where they still work.

### The rebase on 056 (`tool()` security fixes), if 056 lands first

`git merge-tree` onto today's main is clean (EXECUTED), but 056 touches the same file. What to check at that rebase (INFERRED from the two diffs' shape; 056's spec is not on disk yet):
- `tools.py`: 049 renames seventeen constants at every use and rewrites `tool`'s docstring and adds the two overloads directly above it. A 056 hunk that uses an old name (`MAX_ABANDONED`, `TOOL_REQUEST_BYTES`) can merge without a conflict and fail only at run time; `ruff check` (F821) and the full judge catch it, so both must run after the rebase. A 056 test using `T.<old name>` needs the rename too, which is a judge change.
- If 056 changes `tool`'s signature or defaults, both overloads must be edited by hand (criterion 7 fails until they match), and the snapshot and the README block regenerated; the rebase review checks that the snapshot diff is exactly 056's change.
- If 056 writes "(spec 056)" in `tool`'s or `Tool`'s docstring, as the project's habit is, criterion 5's spec-reference count fails after the rebase; the citation moves to a `#` comment.
- If 056 touches `runner._check_tools`, whose signature 049 changed (the `limits` argument), run F2's `ast` rule or a `grep` for `DEFAULTS` loads in `runner.py`, since criterion 10 would not see a direct read.
- CHANGELOG: both add to 0.1.0a4; a trivial conflict.

## Constitution checks

- §4.1 upstream patches: none touched. §4.2 pins: none touched. Not build-class (READ: no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or workflow file in the diff).
- §4.9 / AGENTS.md "tests count operations": the new checks count names, lines, reads and lock entries; no time is read (READ, the check file).
- §4.13 no dependency without a reason: `pyproject.toml` unchanged; no type checker added, as Decision 12 reasons (READ).
- Embedder-neutral names: `defaults`, `set_defaults`, `stats`, `Defaults` name no embedder (READ).
- Judge changes are declared: the new check file, `api.py`, the snapshot, the wheel rule and its stand-in, and the 27 renamed lines; the judge-hash line shows them (EXECUTED). The lane accepts with `--accept-judge`.
- §7 never-do list: nothing tripped. No artifact in git; no edit to `known_gaps.toml` or `context/progress/` (READ, diff stat).

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers, from `build/reviews-evidence/049-buildreview/disposition.md` and the specification's "Revised against the build review"; the branch is not rebased.

1. F1 — fixed in `bc5292e`. The README now says "keyword-only arguments whose default keeps today's behaviour" and "dataclass fields placed last with a default (or keyword-only)". It also says the judge fails until the snapshot is regenerated, and only a specification that lists the change regenerates it, which its review checks.
2. F2 — fixed in `22cd0bf`. Criterion 10 gains an `ast` rule: `runner.py`, read from `runner.__file__`, loads `DEFAULTS` only inside `_current_defaults`. Its lock stand-in now replaces the binding on enter, so `set_defaults` must return what it read inside the lock.
3. F3 — fixed, not softened, in `cccc3b9`, with Decision 2's text in `94f148e`. `_submit` reads `_current_defaults().async_workers` under `_pool_lock`, at submit time. `checked["async_workers"]` is gone. Decision 2 now says the pool's size is process state, the one exception to one read per call. A new check, `test_the_pool_takes_the_newest_size`, was seen failing on the per-call wiring with `(8, 3)`.
4. F4 — fixed in `94f148e`. Decision 10 now states both rules.
5. F5 — fixed in `cf4c1ec`, with Decision 9's text in `94f148e`. The render records each `dataclass()` parameter that differs from its default: `dataclass Tool: frozen, eq=False` in the snapshot, and `@dataclass(frozen=True, eq=False)` in the README. Criterion 1's stand-in also drops `eq=False`.
6. F6 — fixed in `94f148e` and `c642fc3`: the status line, Decision 13 and the Design table.

## Verdict

Lands once F1 and F2 are fixed: the surface, the snapshot, the documentation rules and the one-read wiring are right and hold under every mutation I tried. But the README's promise is looser than Decision 8, and criterion 10 would not catch a regression of the very two properties it exists to guard. F3 to F6 may be fixed or answered in writing.

One line: 049 is correct and well-checked; fix the README's one missing phrase and make criterion 10 see a direct read and an outside-the-lock read, then it lands.

## Confirmation (2026-10-18)

The same reviewer checked each answer against its finding. I read the revision commits `bc5292e`, `22cd0bf`, `cccc3b9`, `cf4c1ec`, `94f148e` and `c642fc3` (`git diff 9e0bc0c..HEAD`) and the author's disposition. Nothing tracked was edited and nothing was committed. Scripts and logs are in `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/049-buildreview/`.

**What I ran (EXECUTED, `uv run` only):**
- `mutate.py` again, on a fresh `git archive HEAD` copy (`mutate-revised.log`). Every mutation caught before is still caught, by the same lines. The F5 mutant (`eq=False` dropped from `Tool`) is now caught too: `-dataclass Tool: frozen, eq=False` / `+dataclass Tool: frozen`, with `--check` exiting 1.
- Criterion 10 and the new pool check, run with `PYTHONPATH=<copy>/src` against five copies. Each copy printed its own `wasi_python.__file__` first (`f2f3-mutants-confirm.log`):
  - control: 2 passed;
  - `_check_places` reading `DEFAULTS.file_calls` directly: fails, "DEFAULTS read outside _current_defaults: ['runner.py:1159']";
  - `old = _runner.DEFAULTS` moved above the lock: fails, "the old value is read inside the lock";
  - the lock removed: fails the same way;
  - the pool size read in `_submit` just *before* `with _pool_lock:`: **passes** (N1 below).
- `api.py --check` on Python 3.11, 3.12 and 3.13 (`--no-project --offline`): exit 0 each. The new `__dataclass_params__` fields exist on all three.
- The fast tier, `uv run pytest -m "not slow"`, on the frozen set `s-f94dec535086b06c` (`build/review-confirm-fast.log` in the worktree): exit 0; `wasi_python v1: 269/287 pass · 0 gap · 10 blocked · 0 fail · 8 deselected`; v1.4 136/136; `ratchet vs 01238501f8: lost 0 · absent 0 · unrun 0 · unrun locally 8 · gained 11 · grew 0 · not selected 8`; `1203 passed, 18 skipped, 8 deselected`. `ruff check` and `ruff format --check` are clean.
- I did not re-run the full judge. The builder's `build/judge-revised.log` reads `276/287 pass · 0 gap · 11 blocked · 0 fail`, `lost 0 · gained 11 · grew 0`, and `1210 passed, 19 skipped`. That matches my first full run plus one new check, and the fast tier agrees (AGENTS.md rule 3a).

**Each finding against its answer:**
- **F1, confirmed.** `README.md:1216-1230` now says what Decision 8 says, and the line about the judge is accurate (READ).
- **F2, confirmed.** Both of my mutants now fail, with messages that name the defect (EXECUTED). The `ast` rule reads the file the test imports, so a copy is tested as itself.
- **F3, confirmed.** The code is right (READ, `runner.py:597-618`):
  - `_submit` reads the size under `_pool_lock`, as main did before 049.
  - `set_defaults` takes only `_defaults_lock` and never `_pool_lock`. No lock is held across both, so the two cannot deadlock.
  - Reading the module global is a single reference load, so a racing `set_defaults` gives `_submit` either the old object or the new one, whole.
  - The newest value always wins, so the "up to 12 at once" after one change is true again.
  - A call's other limits still come from the one read in `_checked`. The exception is stated in Decision 2 and in `_checked`'s and `_submit`'s docstrings.

  One weakness is in the check, not the code (N1).
- **F4, confirmed.** Decision 10 states both rules: lines 403 and 408 of the spec, and the revision notes (READ).
- **F5, confirmed.** EXECUTED above. The snapshot diff is exactly the `Tool` line, and the README block is regenerated.
- **F6, confirmed.** The status line is current ("awaiting the reviewer's confirmation" is now true), and Decision 13 and the Design table say C2 (READ).

**New, from the revision:**

N1 (low). **`test_the_pool_takes_the_newest_size` cannot tell "read under the lock" from "read just before it"** (`tests/checks/test_v1_4_public_api.py`, `_Racing`). `run_async` takes `_pool_lock` first in `_register_exit_hook`, so `_Racing` swaps the defaults there, before `_submit` runs.

Failure (EXECUTED, `mut/pool`): moving the read to `stale = _current_defaults().async_workers`, just above `with _pool_lock:` in `_submit`, passes the check. That reopens a narrow form of F3's race: a `set_defaults` between the read and the lock lets a stale size replace the pool.

The check catches the per-call wiring it was written against, and the code as built reads under the lock, so nothing is wrong today. A fix that works: `_Racing.__enter__` sets a *new* `async_workers` on every entry, and the test asserts the pool's size equals the last one set. In a scratch copy, that version passes on the built code and fails on `mut/pool` with `assert 4 == 5` (EXECUTED, `n1-confirm.log`). Fixing it before landing is a few lines. It may also be written down and fixed with the next change to `_submit`; I do not hold the landing on it.

Note, no change asked: `wasi_python._defaults_lock` is not re-made after a fork, unlike the runner's own locks (`runner.py:931-933`). A child forked while another thread holds it, which is two assignments long, would block in `set_defaults`. That is vanishingly unlikely, and it matches how `__init__.py` held no lock before.

**The rebase on 056** is unchanged from the review, with one item gone: `_check_tools` no longer feeds the pool, and F2's `ast` rule now catches a direct read that 056 might add.

### Verdict on the revision

**Confirmed, it lands.** F1 to F6 are fixed as their answers say. The two properties criterion 10 guards now fail on their mutants. The pool takes the newest size again, under its lock, with no new lock order. N1 is a low gap in the new check's reach, not a defect in the code. It may be fixed before landing or recorded. The lane accepts with `--accept-judge` after the rebase.

One line: every finding is fixed and checked; 049 lands, and N1 (make the pool check's race land on the last lock entry) is optional polish.

## Rebase check (2026-10-18)

The same reviewer checked the rebase delta. The branch was rebased onto main `90e46cb` (035 and 056 landed, 0.1.0a4 released, version 0.1.0a5); the new HEAD is `1e8ff24`. I compared it with what I confirmed, which ends at `b015484`, the N1 fix. Nothing tracked was edited and nothing was committed. Logs are in the scratch folder named above.

**What I ran (EXECUTED, `uv run` only):**
- **The commits.** `git range-diff 1c0123c..b015484 90e46cb..7dd706b` (`range-diff.txt`): 11 of 13 commits are `=`. Step 2 differs only by the version line (`0.1.0a5`), 056's two new private constants in context, and 056's `proceed` lines kept in `_Work.__call__`, with `_FAULT_CHARS` on the `denied` line. Step 5 differs only by the CHANGELOG: the entry replaces 0.1.0a5's "(what changed)" placeholder, and 0.1.0a4's released section is main's, unchanged.
- **The builder's AST claim holds** (`astcmp.py`). Main's `tools.py`, with the seventeen renames applied, equals the branch's `tools.py` once docstrings are stripped and `__all__` and the two `@overload` stubs are dropped: 122 statements each, `equal: True`.
  - `cli.py` is equal too.
  - `mounts.py` differs only in `Mount`, and the protocol stubs' docstring-for-`...` bodies.
  - `runner.py` differs only in the 049 functions: `Defaults`, `run`, `run_async`, `_submit`, `_checked`, `_check_tools`, `_check_places`, and the new `_current_defaults`. Main did not touch `runner.py` after `1c0123c`.
  - `__init__.py` differs only by 049's own changes.
- **056's tests are untouched.** `git diff 90e46cb HEAD -- tests` shows only 049's new files, the wheel rule, and the 27 renamed lines. 056's four embedding checks and three unit cases are byte for byte main's. `git grep` finds no old constant name anywhere in `src`, `tests`, `scripts`, `.github`, `recipes` or the README.
- **The surface did not move.** `api.py --check` exits 0, with no regeneration.
- **The 21 mutations** (`mutate-rebased.log`) give the same outcome as at the confirmation, line numbers aside.
- **The checks against their mutants** (`rebase-mutants.log`, each copy importing itself):
  - control: passes;
  - the direct `DEFAULTS` read: fails, `['runner.py:1159']`;
  - the old value read outside the lock: fails;
  - the pool size read just above the lock (N1): fails, `assert 2 == 3`;
  - the original per-call pool wiring: fails twice (one read per call, `3 == 2`; and the pool check, `(8, [2, 3])`).
- **The fast tier**, `uv run pytest -m "not slow"`, with `WASI_PYTHON_ARTIFACTS=<main>/build/sets/s-c4190ca065ada03a` (035's frozen set), in the worktree (`build/review-rebase-fast.log`): exit 0.
  - `wasi_python v1: 294/343 pass · 0 gap · 10 blocked · 0 fail · 39 deselected (unit suite 1056/1064, 8 skipped)`;
  - v1.4 140/140;
  - `ratchet vs 4921daffeb: lost 0 · absent 0 · unrun 0 · unrun locally 8 · gained 11 · grew 0 · upstream unrun 31 · not selected 27`;
  - `1350 passed, 18 skipped, 39 deselected`. These are the builder's fast-tier numbers.
  - `context/progress/` is identical to main's, so "lost 0" is measured against the state that accepted 056. Every 056 check that ran still passes.
  - `ruff check` and `ruff format --check` are clean.
  - I did not re-run the full judge. The builder's `build/judge-rebased.log` (301/343, 0 fail, lost 0, gained 11, grew 0) agrees with the fast tier.

**On each part of the delta:**
- **056's behaviour survives exactly** (the AST comparison):
  - partial-bound keywords are left out of the schema and refused in a frame;
  - the `proceed` check runs after the gate and before the tool;
  - `_Bounded._proceed` is taken under the bound's lock.

  The tool docstring 049 rewrote did not exist in 056's diff, so no 056 text was lost. 056's "(spec 056)" citations are in private docstrings (`_Work.__call__`, `_bound_keywords`, `_Bounded._proceed`), which criterion 5 does not read. Criterion 5's counts are 0 in the fast tier.
- **Criterion 6 holds** on 056's and 035's new README prose: 0 spans, 0 docstring hits.
- **N1 is fixed** in `b015484`/`7dd706b`. `_Racing` sets a new `async_workers` on every entry to the lock, and the check asserts the pool's size is the last one set. My mutant now fails. The "never the value read before" guard keeps the first swap from equalling the old size.
- **The CHANGELOG** is right to put the entry under 0.1.0a5. The renames are now a change from the released 0.1.0a4, which alphas allow (Decision 8). The entry says so, and says that assigning `wasi_python.runner.DEFAULTS`, as a4's README taught, still works.

Nothing remains.

### Verdict on the rebase

**Confirmed, it lands.** The rebase changed only what the two recorded conflicts say. 056's code and checks are intact, the surface and its README block are unchanged, every mutant is still caught, and the fast tier on 035's set is green with lost 0 and grew 0. The lane accepts with `--accept-judge`.

One line: the rebase is faithful, so 049 lands as confirmed.
