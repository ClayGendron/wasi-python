# Review of 168 — The POSIX hosts have a module of their own

- **Date:** 2026-10-30
- **Reviewer:** an agent (Claude Opus), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** the specification as drafted, `context/specifications/168-the-posix-hosts-have-a-module-of-their-own.md`, at `4849fc4e` on `docs/0.1.3-specifications`, and its drafter's prototype, a scratch copy of the package outside the repository, diffed against that commit
- **Run:** none: a specification review
- **Re-ran:** on the prototype, `uv run pytest -q tests/unit/test_runner_grants.py tests/unit/test_runner_threads.py tests/unit/test_runner_calls.py tests/unit/test_runner_sweep.py tests/unit/test_runner_module_caches.py tests/unit/test_runner_module_cache_read.py tests/unit/test_snapshot.py tests/unit/test_runner_package.py` → 258 passed, 34 skipped (the 254 of criterion 8 plus `test_runner_package.py`'s 4), exit 0; the rules checks by keyword (platform, order, by name, one module, ceiling, eighty, seam, module level, mypy, api lists) → 15 passed, 1 skipped; `tests/unit/test_typecheck.py` → 2 passed; `tests/harness/typecheck.py` → "both passes are clean"; `tests/harness/api.py --check` → exit 0; `ruff check src tests` → "All checks passed!"; `ruff format --check src tests` → 196 files formatted. A move check of my own (an `ast.dump` of every top-level node of the base's `_platform.py` against its node after the split).
- **Time box:** 45 minutes (structural); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

EXECUTED, the move: of the base's top-level names, 40 are in `_platform_posix.py` and 13 stay; none is gone; one is new, `_open_flags`. Five moved nodes differ from the base, `_DIR`, `_DIR_OPEN`, `_CACHE_DIR_OPEN`, `_CACHE_FILE_OPEN` and `_fd_name`, each only where `_flags(` became `_platform_common._flags(` (and ruff re-wrapped `_DIR` and `_DIR_OPEN`). `_conforms`'s `if TYPE_CHECKING:` block moved place only. Step 4's script reads the call back as `_flags`, so it reports no difference; both readings agree.

READ: AGENTS.md; constitution §4, §5.6, §7; `context/reviews/README.md`; the specification; 162's Decisions; `src/wasi_python/_platform.py` (the docstring, `_flags`, `_same_file`, `_select`, `_conforms`), `_platform_common.py`, `_private_dirs.py:38` and `:173`, the imports at `_call.py:30`, `_sessions.py:38`, `_places.py:21`; `tests/checks/test_rules.py` (`PLATFORM_MODULE`, `_platform_hits`, `PLATFORM_HALVES`, `LONG_FUNCTIONS`); `tests/unit/test_runner_package.py` (`ORDER`, `LATE`, `_once_errors`); `tests/harness/api.py` (`RUNNER_FILES`); `tests/unit/test_typecheck.py`; `pyproject.toml`'s mypy settings; `tests/harness/news.py` (`HEADINGS`); `context/changes/README.md`. Every line number Decision 5 cites names the moved class it says (EXECUTED, `grep -n`).

## Acceptance criteria against evidence

1. Sizes — met on the prototype: 211, 1,165, 365, 502 (EXECUTED).
2. The direction — met on the prototype: `ORDER` passes with `_platform_posix` between Windows and the door; the module imports `_platform_common` and `_process`, and `_wasmtime_ffi` late (READ, EXECUTED).
3. The choice — met: `_select` is unchanged to the byte (READ, diff); 3 platform reads, all in `_select`, before and after (EXECUTED). The fault of step 3 is the drafter's; I did not plant it.
4. A move — met, with Finding 3's reading of "byte for byte" (EXECUTED).
5. Types — met: both passes clean; `type: ignore` unchanged (EXECUTED).
6. No seam, no long function — met: rules green; no moved function changes length (EXECUTED).
7. Nothing public — met: `api.py --check` exit 0 (EXECUTED).
8. The renamed tests — met: 258 = 254 + 4 (EXECUTED).
9. Every host — not yet evidenced: needs the pull request's run with macOS, as the criterion says.

## Findings, most severe first

1. **Low: the news file's heading does not exist, and its words break the entry rules** (`tests/harness/news.py:61`, `context/changes/README.md`). `HEADINGS` holds New, Faster, Security, Fixed, Upgrading and For contributors; there is no `### Changed`. An entry names no specification and no private module, and this one names "spec 168", `_platform.py` and `_platform_posix.py`. Failure: `ci-status` refuses the news file on the first push. Fix text, "The news file": "Under `### For contributors`: **The platform code is split by host family.** The POSIX, Linux and macOS hosts now have a file of their own beside the Windows one, and the interface and the choice stay where they were. Nothing an embedder sees changes. [Contributing](https://claygendron.github.io/wasi-python/contributing/first-change/)".
2. **Low: the sibling it names is the wrong one.** The Depends line and The problem say 162 adds the copy-on-write restore; 162's Decision 10 makes that its own specification, and 162 needs nothing of 168 (READ). Failure: a scheduler holds 162 behind 168 for no reason. Fix text, Depends: "Lands before the copy-on-write restore's specification (162, Decision 10): its protocol line goes in `_platform.py`, its POSIX half in `_platform_posix.py`. 162 itself does not wait on this one." The problem: "162's copy-on-write follow-up is that next change."
3. **Low: "byte for byte" is not quite true.** Five moved nodes read `_platform_common._flags`, and ruff re-wraps two (EXECUTED). Fix text, Decision 2: "byte for byte, but for `_flags`, read as `_platform_common._flags` in `_DIR`, `_DIR_OPEN`, `_CACHE_DIR_OPEN`, `_CACHE_FILE_OPEN` and `_fd_name`, which step 4 reads back".
4. **Low: the judge's lists are named without their files.** `ORDER` is in `tests/unit/test_runner_package.py`, `RUNNER_FILES` in `tests/harness/api.py`, `PLATFORM_HALVES` and the comments in `tests/checks/test_rules.py` (READ). Fix text, Design's "The judge": name the three files, and the news file's `[claim.judge]` gives each its reason.
5. **Low (a note, not a fix): the POSIX classes are not held as the Windows class is.** `_platform_hits` refuses `_Windows` named outside `_platform.py`; `_platform.py` still binds `_Linux`, `_Darwin` and `_Posix`, so `_platform._Linux()` would make a platform outside `_select`. That was so before the split, so nothing regresses. Fix text, Decision 7: "The per-host cut extends `_platform_hits` to the POSIX classes."

## Structure

The rubric's rows, against the 0.1.2 structural review's scores. Measured on `4849fc4e` and on the prototype (EXECUTED).

| measurement | before | after |
|---|---|---|
| `_platform.py` lines | 1,351 (90% of 1,500) | 211 |
| largest platform module | `_platform.py` 1,351 | `_platform_posix.py` 1,165 (78%) |
| all of `src/` | 15,993 | 16,026 (+33: a docstring, imports, the delegate) |
| platform reads | 3, in `_select` | 3, in `_select` |
| module-level mutables and locks (the README's grep) | 0 | 0 |
| private-API lines outside `_wasmtime_ffi.py` (the README's grep) | `_places.py` 1, `_tool_host.py` 1 | the same |
| functions past 80 lines | `LONG_FUNCTIONS` only | unchanged |

- R1 Contract: unchanged; nothing public moves (`api.py --check`).
- R2 Safety: unchanged; the code is the same code.
- R3 Layering: holds Strong. One more module, edges pointing down only; the two host modules never import each other; the private API stays behind the late `_wasmtime_ffi` import.
- R4 Process state: unchanged; no mutable moves.
- R5 Portability: Strong, headroom restored. Each family in its module, chosen once. `reviews/README.md`'s "the two below it" becomes three at the disposition, as Scope says.
- R6 Testability: unchanged; the tests name the classes where they live and patch only the platform object.
- R7 Evolvability: moves toward Strong; closes the 0.1.2 review's M1 for `_platform.py`. `_call.py` at 1,361 stays M1's other half, out of scope.
- R8 Operability: unchanged; no message changes.

## Constitution checks

- §4.13: ruff, format and the type checker green on the prototype (EXECUTED).
- §5.6: this is the structural pre-build review; nothing here touches the guest, the artifact set or the recipe.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. to 5. Lows with fix text; they need no round.

## Verdict

Fit to build: no High or Medium; Lows 1 to 4 are written-in fixes the builder applies with the text above, and Low 5 is a note for the per-host cut.
