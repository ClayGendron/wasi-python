# Review of 105 — the no-fork child's fix (`727bd4c`)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent started by the lane; wrote none of the chain 103-109 or this fix
- **Reviewed:** `727bd4c` on `dbecd2d` (two files: `tests/checks/test_v1_4_embedding.py`, +2 -1;
  `context/specifications/105-one-owner-for-the-process-state.md`, the landing-notes bullet)
- **Run:** none dispatched (the lane's brief: single node ids and ruff only; the Windows leg is the
  wave's dry run). Time box: 25 minutes.
- **Re-ran:** `uv run ruff check` and `ruff format --check` → exit 0;
  `uv run pytest test_v1_4_embedding.py::test_a_forked_child_is_refused tests/unit/test_runner_grants.py
  tests/unit/test_runner_threads.py` → 46 passed, 2 skipped, exit 0 (darwin, fork branch);
  the `NO_FORK` child program run alone on darwin → `["True b'ran\\n'", "{'used': True, 'forked': False}"]`
  (EXECUTED; the first line is `True` only because darwin has `register_at_fork`). Output in
  `build/105-fix-review/`.

## What was read

- `git show 727bd4c`; `git show dda6075:tests/checks/test_v1_4_embedding.py` (the pre-chain
  `NO_FORK` printed `runner._fork`; the expectation was the same literal).
- `src/wasi_python/_process.py:118-119` (`fork_used`, `forked`, plain bools, default False),
  `:209-210` (the child sets `forked` only if `fork_used`), `:235` (the fork hook is registered
  only where `register_at_fork` exists); `src/wasi_python/_engines.py:87` (`fork_used = True`
  before the first engine, on every platform). Against `dda6075:src/wasi_python/runner.py:1412,
  1457-1458, 4110`: `_fork["used"]` ↔ `fork_used`, `_fork["forked"]` ↔ `forked`, set at the
  same points. The labels mean the old dict's keys.
- `src/wasi_python/_platform.py` `_Windows` (1096-1390) against the `_Platform` protocol.

## Acceptance against evidence

1. The expectation is unchanged — met: the asserted list in the no-fork branch is byte-identical
   to `dda6075`'s (READ); only the child program's print changed.
2. The same fields, from their new owner — met: the two keys are printed from `process()`, which
   now owns them, under the old names, so the line still shows "used, not forked" (READ, and
   EXECUTED for the second line on darwin).
3. No weakening — met: no expectation, gap, allowance or golden file is touched; the check still
   asserts both lines in full (AGENTS.md rule 4).
4. Nothing else changed — met: `--stat` shows the two files; the docstring's dropped "(spec 015)"
   predates this commit (the chain's).

## Spot-checks of the builder's scan (the three riskiest)

1. `tests/unit/test_runner_grants.py:305-345` `_WinFake.install`: patches `open_handle` and
   `close_held` on a real `_Windows()`, and `process().observers.drive_folder`; all three exist
   (`_platform.py:1128, 1236`; `_process.py:87`, read at `_platform.py:1161`). Clean.
2. `tests/unit/test_runner_threads.py:128`: `_Windows().tell_interpreter(...)` with the keyword
   set the protocol names; `_Windows` returns False (`:1363-1373`). Clean.
3. `tests/unit/test_runner_calls.py:345`: `trap_handlers_ready` with `host=_Windows()` and a
   failing `handler_base`; `_Windows.trap_handlers_ready` accepts `handler_base` and returns None
   (`:1375-1381`). Clean.

Both unit files passed here (EXECUTED, darwin); their Windows leg is the dry run's.

## Findings, most severe first

None. Note: the darwin run does not exercise the no-fork branch; its Windows pass is INFERRED from
the second line's identity above until the next dry run's Windows own-embedding job reads green.

## Verdict

Lands.
