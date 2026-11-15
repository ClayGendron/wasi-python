# Review of 178 — The runner's entry points share one argument check and one async wrapper (before it is built)

- **Date:** 2026-11-14
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** the specification as drafted, `context/specifications/178-the-runners-entry-points-share-one-check.md` at `1b78e11b` on `spec/178-the-runners-entry-points-share-one-check` (from `dev` at `25e49df5`), against `src/wasi_python/runner.py` whole, `_outputs.py` (`OutputFeed`, `_Late`, `_claimed`, `_check_on_output`), `_process.py`, `_places.py`'s imports, `tests/unit/test_runner_package.py`, `tests/checks/test_rules.py` (`LINE_CEILING`, `ALLOWED`, `SEAM_ALLOWED`, `LONG_FUNCTIONS`), `tests/harness/api.py`, `tests/harness/scan.py` (`RUNNER_MODULE`, `long_function_hits`), and every test that names a moved name.
- **Run:** none; a pre-build review has no pull request run. Nothing dispatched, no `gh`.
- **Box:** 45 minutes (structural); kept.
- **Re-ran:** on the base, the four shape checks, the five rules of Decision 6, `test_set_defaults_changes_what_run_reads`, `test_the_pool_takes_the_newest_size` and `test_a_feed_used_twice_is_refused` → 12 passed (EXECUTED). Then a prototype of my own, built by a script from the specification's text alone, in a scratch copy outside the repository (`git archive` of `1b78e11b`), not the drafter's:
  - `wc -l`: `runner.py` 1,101, `_entry.py` 412 (EXECUTED).
  - The `ast` lengths: `run` 183, `run_async` 188, `Session.__init__` 187, `Session.run_async` 73, `_checked` 79, `_check_tools` 74, `_submit` 45 (its signature wraps), `_awaited` 55, `_serving` 9 (EXECUTED).
  - `LONG_FUNCTIONS` set to six entries; the shape and rules checks by keyword (order, by name, one module, ceiling, eighty, seam, lock, mutable, bound twice, api lists, mypy) → 17 passed; `tests/harness/typecheck.py` → "both passes are clean"; `tests/harness/api.py --check` → exit 0; `ruff check` and `ruff format --check` clean; `uv run pytest tests/lint` → 14 passed (EXECUTED).
  - Step 3's fault, `from . import runner` planted in `_entry.py`: `_entry.py:22 (_entry imports runner, not before it in ORDER)`; removed, green (EXECUTED).
  - Step 4's comparison by `ast.dump`: seven moved names identical, `_checked`, `_check_tools` and `_submit` differ, two new names `_awaited` and `_serving`, none left in `runner.py`, none lost (EXECUTED).
  - The criterion 7 files plus `test_snapshot.py` and `test_v1_4_public_api.py`, with no artifact set on this machine: 175 passed, 421 skipped, 4 failed on both the base and the prototype, the same node ids passing (EXECUTED, a `diff` of the `-rA` lists). The four fail on the base too (a hostile-guest triangulation and three embedding rows), so they are this machine's, not the change's.
  - A probe of the prototype's `_awaited` with no guest: a call returns its value with `live` empty; a running call cancelled sets its event and is awaited before `CancelledError`; a queued turn cancelled runs its claim and its release once; a refused submit releases the claim; `live` empty after each (EXECUTED).
  - `import wasi_python` loads neither `asyncio` nor `concurrent.futures`, on the base and on the prototype (EXECUTED).

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

## Acceptance criteria against evidence

1. Sizes — met on the prototype: 1,101 and 412, under 1,150 and 460 (EXECUTED).
2. The order — met on the prototype, the fault seen red with its line (EXECUTED).
3. A move — met on the prototype: exactly Decision 3's three names differ, and two are new (EXECUTED). `_checked`'s difference includes its docstring (finding 2).
4. Long functions — met on the prototype: six entries, `run` 183, `run_async` 188, nothing in `_entry.py` past 80 (EXECUTED).
5. No seam, no state — met on the prototype; `SEAM_ALLOWED` untouched; the mutables grep gives 0 lines on both (EXECUTED).
6. The defaults — met on the prototype with Decision 5's edits (EXECUTED).
7. Behaviour — not testable here without the set (skips as above). The list misses the one check of `Session.run_async` on a real guest (finding 4).
8. Nothing public — met on the prototype (EXECUTED).
9. Types and words — met on the prototype; `type: ignore` 4 → 4, `Any` 486 → 490, from the `tuple[Any, ...]` of `build` (EXECUTED).
10. The run — only the pull request can show it.

Every line Decision 5 cites names what it says: the patch grep gives `DEFAULTS` 4, `_current_defaults` 1, `run` 3; the calls are at the lines given; `test_v1_4_public_api.py:417` and `:423` read and patch `_current_defaults`; `Session.__init__` passes `limits` at `runner.py:1051` (EXECUTED, READ). Decision 2's spans and lengths match an `ast` walk (EXECUTED).

## Findings, most severe first

There is no High and no Medium. The import graph stays acyclic, since the one upward name is under `TYPE_CHECKING`, as `_places.py:26` has it. Every rule the move must keep was green on my prototype. No check is weakened: each test edit changes a call site, and the expectations stay the same.

1. **Low: one more step moves in `run_async` than Decision 4 says** (`runner.py:512-513`). Today the running loop is got before `_engines._wasmtime()`. In `_awaited` it is got after. This shows only for a coroutine stepped with no running loop where wasmtime-py cannot load: it raises `ImportError` where it raised `RuntimeError` (INFERRED). Fix text, Decision 4's last paragraph: "…and the session's `threading.Event()`, made before its claim instead of after. In `run_async` the running loop is got after `_engines._wasmtime()`, not before. That differs only for a coroutine stepped with no running loop where wasmtime-py cannot load."
2. **Low: `_checked`'s docstring changes too** (`runner.py:719-723`). Its "The defaults are read once, here" becomes false. Fix text, Decision 3's first bullet: "Its docstring says the `limits` are the ones its entry point read, once."
3. **Low: `asyncio` and `concurrent.futures` must stay late** (Decision 1). `runner.py` imports both inside functions or under `TYPE_CHECKING`, so `import wasi_python` loads neither (EXECUTED). No check holds that, and a module-level `import asyncio` in `_entry.py` would pass every rule. Fix text, Decision 1: "As in `runner.py`, `asyncio` and `concurrent.futures` are imported inside the functions that use them, or under `TYPE_CHECKING`."
4. **Low: criterion 7 leaves out the one check of `Session.run_async` on a real guest.** `tests/checks/test_v1_4_sessions.py::test_run_async_on_a_session` holds three things: a running turn cancelled ends the session; a queued turn cancelled leaves it untouched; and the next turn is served. `test_fork_exit_and_the_collector` holds a turn queued at exit (READ, `:651-690`, `:846-871`). These are the paths `_awaited` merges. Fix text, criterion 7, after `test_runner_limits.py`: "`tests/checks/test_v1_4_sessions.py -k "run_async or exit"`,".
5. **Low (a note): no check holds the session turn's feed claim before its checks.** `test_a_feed_used_twice_is_refused` drives `run_async` only, and no session row refuses a turn that holds a feed (READ, grep). Step 4 compares the moved names, not the two rewritten bodies. So the pull request's review must read both bodies against `:477-543` and `:1385-1435`. A matching session row (it needs the set) would hold the order. It would flip with the `run_async` row when L7 is fixed.
6. **Low: Decision 8's reserved line for L7 has no writer.** Scope puts `roadmap.md` out. Fix text, Decision 8: "The 0.1.5 preparation, when it retires 178's line, adds L7's: both halves, the feed claimed after the checks in `_awaited` and `output_keep`'s `TypeError`."

## The two open questions

**The feed's claim (L7's feed half): keep it out, as recommended.** 178's whole case is that it is a move. The `ast` comparison, the unchanged expectations, "no verdict moves" and R1 "unchanged" each rest on that. L7's fix changes behaviour that a check pins, and it flips that check's expectation. Inside a move, a reviewer could no longer say "nothing an embedder sees changes" (INFERRED). After 178, the fix touches one place, not two: `_serving` goes away, and `_awaited`, or the line after the checks, claims the feed. So waiting costs little (INFERRED, from the prototype). With finding 6's line, L7 keeps its own specification and its own claimed judge change.

**`test_v1_4_public_api.py:396` retargeted: as strong as before, for what it could show.** By design, `_checked` no longer reads the defaults. What the line held is now held three ways: `limits` is required, so `_checked` can apply only what its caller passes; the same test's `ast` scan refuses a `DEFAULTS` load outside `_current_defaults` in every module; and the count holds one read per entry point (READ, `:368-376`, `:415-430`). I checked this with two mutants of the prototype's `run_async`. One passed a `DEFAULTS` copied at import, and the scan turned red. The other passed a literal `Defaults(…)`, and the count turned red at `assert 1 == 2` (EXECUTED). Before and after alike, nothing shows end to end that `run_async` and `Session` apply the value they read. `test_snapshot_is_true_false_or_a_snapshot` shows it for `run` only (READ, `test_snapshot.py:355-359`). A stronger check, optional and with no seam, costs three lines. In that test's `set_defaults(small)` block, loop over `run`, `run_async(…, executor=ex)` and `Session(snapshot=snap)`, each expecting `SnapshotMismatch` "memory_bytes is 65,536". It passes on the prototype and is red under the literal mutant (EXECUTED). If it is taken, its file joins the judge change. The helpers at `test_runner_limits.py:122` and `test_runner_tools.py:854` must read `wasi_python.defaults()` at each call, not once, or their `set_defaults` rows (`:147`, `:881`) turn red. Red, not weak, so this needs no fix (INFERRED).

## Structure

Measured on `25e49df5` and on my prototype, by the README's commands (EXECUTED).

| measurement | before | after (prototype) |
|---|---|---|
| `runner.py` lines | 1,476 (98%) | 1,101 (73%) |
| `_entry.py` lines | — | 412 (27%) |
| all of `src/` | 17,330 | 17,367 (+37: a docstring, imports, the wrapper) |
| functions over 80 in `runner.py` | 4 | 3 |
| `LONG_FUNCTIONS` | 7 entries | 6; `run` +1, claimed |
| mutables and locks (grep) | 0 | 0 |
| private-API lines (grep) | 90 | 90 |
| platform reads | 3 | 3 |
| `Any` / `type: ignore` | 486 / 4 | 490 / 4 |

- R1 Contract: unchanged; the snapshot holds, and L7 stays carried.
- R2 Safety: unchanged; every check runs before any effect, in today's order but for finding 1.
- R3 Layering: holds Strong. One node below `runner`, acyclic at runtime; one `TYPE_CHECKING` name points up, as in `_places.py`.
- R4 Process state: unchanged; the same `process()` fields, read at each use; `live`'s two meanings now live in one file.
- R5 Portability: untouched.
- R6 Testability: unchanged; no seam, `SEAM_ALLOWED` 18; the reader is a parameter.
- R7 Evolvability: moves toward Adequate and closes M1 of 0.1.3 and 0.1.4. M2 (115) stays open.
- R8 Operability: unchanged.

## Constitution checks

- §4.10: the specification labels its claims; the inferred lengths it gives agree with my prototype within one line.
- §4.13: ruff, format and the type checker green on the prototype (EXECUTED).
- §5.6: this is the structural pre-build review the Kind line asks for. Nothing touches the guest, the artifact set or the recipe.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. to 6. Lows with fix text or notes; they need no round.

## Verdict

May be built as written: no High or Medium stands. The builder applies the fix text of Lows 1 to 4 and 6. L7 stays out, and the retargeted line is as strong as before, with the optional end-to-end row offered above.
