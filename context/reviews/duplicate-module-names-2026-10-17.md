# Review of a judge change — no module-level name bound twice

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change. I read `AGENTS.md`
  (rules 4, 6 and 8), `context/reviews/README.md`, and finding 9 of
  `context/reviews/019-the-command-line-2026-10-17.md` with its disposition. Each claim is
  labelled EXECUTED or READ.
- **Reviewed:** the uncommitted diff on `98d0210`: `tests/harness/scan.py` gains
  `duplicate_name_hits`; `tests/checks/test_rules.py` gains
  `test_no_module_level_name_is_bound_twice`; `tests/unit/test_scan.py` gains
  `test_a_name_bound_twice_at_module_level_is_found`.
- **Re-ran (EXECUTED, darwin-arm64):**
  - `uv run pytest -q tests/unit/test_scan.py tests/checks/test_rules.py` → 94 passed, exit 0.
    Scoreboard: rules 18/18; ratchet vs `84f4e1c525`: lost 0, gained 1, grew 0; judge changed:
    the three files above.
  - `uv run ruff check src tests` → all checks passed, exit 0 (ruff 0.17.1).
  - `uv run ruff format --check src tests` → 52 files already formatted, exit 0.
  - No tracked file was edited. Probes and logs are under
    `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev-dupnames/`
    (`probe/`, `run_probe.py`, `probe.log`, `strict.py`, `strict.log`, `pytest.log`).

## Acceptance criteria against evidence

1. It catches the bug that lost two spec 015 checks — **met (EXECUTED).** A copy of
   `tests/checks/test_v1_4_embedding.py` with a second `CTRL_C = r"""..."""` appended gives
   `tests/checks/test_v1_4_embedding.py:1287: CTRL_C (first bound at 548)`. The unmodified file
   gives no hit (the real tree passes).
2. The judge is not weakened — **met (READ).** The change adds one check and one unit case. No
   existing check, golden output, `tests/known_gaps.toml` or `context/progress/` file is touched.
   The run reports the judge change, so landing needs `--accept-judge "<reason>"`.
3. The real tree passes — **met (EXECUTED).** Zero hits over `tests`, `src`, `scripts`,
   `release`.
4. Guest programs under `tests/jobs/` may rebind working names — **met, but more widely than
   stated** (finding 1).

## Findings, most severe first

1. **Low. The working-name exemption covers every file, not only `tests/jobs/`**
   (`tests/harness/scan.py:671-673`). The comment and the commit's reason say guest programs
   rebind on purpose. The code exempts any lower-case non-function name in any file.
   Failure (EXECUTED, `probe/tests/checks/fn_lower.py`): `script = "one"` then `script = "two"`
   in a check module → no hit. Today the check files name their scripts in upper case (`CTRL_C`,
   `COMMAND_CTRL_C`), so the real bug class is caught. But that is a convention, not a rule; a
   lower-case script constant would slip through. Evidence the stricter rule is cheap: a
   prototype (`strict.py`) that flags **every** name (upper or lower case, tuple targets,
   imports, `if`/`try` bodies) finds 6 hits on today's tree, all in `tests/jobs/`
   (`compress.py` `blob` ×5, `pandas_csv.py` `import dateutil` / `import dateutil.parser`), and
   none elsewhere (EXECUTED, `strict.log`). Fix: exempt by path (`tests/jobs/`), and flag all
   names elsewhere; or answer in writing that upper case is the convention for constants.
2. **Low. Tuple and starred targets are not seen** (`scan.py:665`). Only `ast.Name` targets are
   collected. Failure (EXECUTED): `A, B = 1, 2` then `A = 3` → no hit; `A = 1` then
   `A, B = 3, 4` → no hit; `A = 1` then `*A, B = [1, 2]` → no hit. Fix: walk `ast.Tuple`,
   `ast.List` and `ast.Starred` targets recursively (a five-line helper; `strict.py` has one).
3. **Low. Imports are not bindings to this rule** (`scan.py:661-667`). Failure (EXECUTED):
   `A = 1` then `import os as A` → no hit; `def f` then `from os.path import join as f` → no
   hit. Ruff's F811 does catch both in `src/` and `tests/` (EXECUTED, `--select F811`). But
   `pyproject.toml` excludes `scripts/` from ruff (READ), so there nothing catches them. Fix:
   count `Import`/`ImportFrom` names; `import a.b` binds `a`, so a repeated package import
   (`pandas_csv.py`) must not count, or only count when the other binding is not an import.
   Or answer: ruff covers `src/` and `tests/`, and `scripts/` is out of scope.
4. **Low. Names bound inside module-level `if`/`try`/`for`/`with`, by walrus, or by `global`
   in a function are not seen.** Failure (EXECUTED): `A = 1` then `if True: A = 2` → no hit;
   the same for `try:`, `for A in ...`, `with ... as A`, `print(A := 2)`, and
   `def g(): global A; A = 2`. These are rare in check files, and `if`/`try` branches are often
   real alternatives (`try: import tomllib / except: tomllib = None`; `if TYPE_CHECKING: ...
   else: ...`), so a naive walk would raise false positives. A fair answer: leave them, and say
   so in the function's comment. If `if`/`try` bodies are walked, a name bound once in the body
   and once in an `else`/`except` should not count.
5. **Low. Two legitimate patterns would trip it later** (`scan.py:661-663`). Failure
   (EXECUTED): three `@overload`-decorated `def f` → two hits; `functools.singledispatch` with
   two `@g.register def _` → one hit. Neither pattern is in the tree today (READ: grep finds no
   `overload` or `singledispatch` under `src`, `tests`, `scripts`, `release`). Fix when needed:
   skip a function decorated with `overload`, and skip the name `_`. Or answer in writing.
6. **Low. The unit case does not pin three behaviours the code has.** Class redefining a
   function (`class_over_fn.py` → hit, EXECUTED), an assignment over a function name, and an
   annotated assignment (`A: str = "one"` then `A = "two"` → hit, EXECUTED) all work but are
   untested. A lower-case name rebound in a non-jobs file (finding 1) is also unpinned, so the
   scope of the exemption is invisible to the judge. Fix: add these to the unit case.
7. **Nit. `import ast` is inside the function** (`scan.py:651`). The module's other imports are
   at the top (READ). Move it up.

### On the reviewer's question 3, false positives on the real tree

- `__all__` set twice: **not flagged** (EXECUTED). `"__all__".isupper()` is false, so dunders
  fall under the lower-case exemption. `__all__ += [...]` is an `AugAssign` and is not seen.
  If finding 1 is fixed by flagging all names outside `tests/jobs/`, a second `__all__ = ...`
  would be flagged; that is the right answer (the first list is silently lost).
- `TYPE_CHECKING` imports: **not flagged** (EXECUTED). `if` bodies are not walked and imports
  are not counted. `src/wasi_python/runner.py:47` uses this pattern (READ) and passes.
- `T = TypeVar("T")` once, and `A: int` (no value) then `A = 1`: not flagged (EXECUTED).
- Augmented assignment (`A += ...`) is not flagged (EXECUTED). That is right: it extends the
  value on purpose and does not drop the earlier binding.

## Constitution checks

- §4 constraints: the change touches no source tree, pin, artifact or download. It runs as an
  `ast` walk over repository files. It counts nothing by wall-clock.
- §7 never-do list: nothing tripped. The judge grows by one check, with its reason in the
  docstring and in finding 9 of the 019 review.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Fixed:** the exemption is scoped to `tests/jobs/`; elsewhere every name bound twice is a hit.
   The real tree has none.
2. **Fixed:** tuple, list and starred targets are counted (a case).
3. **Fixed:** imports are counted (`import os as A` over `A`, a case); this covers `scripts/`,
   which ruff does not lint.
4. **Answered in the function's comment:** names bound inside `if`, `try`, `for` or `with` are
   not counted, since their branches are often real alternatives; walrus and `global` are left.
5. **Fixed:** functions decorated with `…overload` or `….register` are not counted (a case).
6. **Fixed:** cases pin a class over a function, an annotated assignment, augmented assignment
   (allowed), an `if`/`else` pair (allowed), and a constant bound twice in a job (flagged).
7. **Fixed:** `import ast` is at the top of `scan.py`.

1.
2.
3.
4.
5.
6.
7.

## Verdict

**Lands**, once each finding is fixed or answered in writing: it catches the exact `CTRL_C`
redefinition that lost two checks, the tree passes, the tests and ruff are green, and every
finding is a low-severity gap or nit (finding 1, scoping the exemption to `tests/jobs/`, is the
one I would fix before landing, since today's tree already satisfies the stricter rule).
