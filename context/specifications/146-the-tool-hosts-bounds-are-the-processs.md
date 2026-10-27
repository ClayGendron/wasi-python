# 146: The tool host's bounds are the process's

- **Status:** drafted 2026-10-27 from `../research/2026-10-27-a-code-review-of-the-runner-for-production-use.md` (§3); not yet built. It waits for the owner's instruction to build.
- **Date:** 2026-10-27
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/wasi_python/_tool_host.py` (the abandoned count, `_wait`; 1,027 of 1,500 lines, about 20 added), `src/wasi_python/_process.py` (one counter under `tool_threads_lock`, which the lock order already names as a leaf; 237 lines, two lines), rows in `tests/unit/test_runner_tools.py` and `tests/unit/test_tools.py`, paragraphs in `docs/how-to/tools.md`, `docs/how-to/limits.md` and `docs/how-to/mounts.md`, and one measured fact in a short research memo. No new lock, no new seam, no platform branch. No change to `tests/public_api.txt`: the bound is a constant, as `_MAX_ABANDONED` is today.
- **Depends on:** nothing in flight. Landed and unchanged: the tool protocol and its host (031, 036, 110), the per-run budgets (060, 068), the mounts' staging bound (034).
- **Research it stands on:** `../research/2026-10-27-a-code-review-of-the-runner-for-production-use.md`, §3 (Medium 5, Medium 6 and the `ToolError` Low), a fresh sub-agent's read of `_tool_host.py` and `_fs_table.py`, cited by line.

## The problem

A tool that runs past its deadline is marked abandoned and runs on, with the embedder's full authority, until it returns on its own (`_tool_host.py:723-736`). `_MAX_ABANDONED = 4` (`_tool_host.py:38`) bounds the abandoned threads of one call or one session, after which that call's next tool call is refused. Nothing bounds the process: an embedder that runs thousands of calls of untrusted code, each calling one slow tool, accumulates thousands of threads and whatever each holds (READ, the memo's Medium 6). A tool with `timeout_s=None` in a run with no deadline waits in `_wait` without bound (`_tool_host.py:749-769`).

Mount staging is bounded by `memory_bytes` (`_call.py:483`), which is host memory beside the guest's own linear memory of up to `memory_bytes`; a staged file is copied once more for the provider at close or exit (`_fs_table.py:541`). So one guest can hold about three times `memory_bytes` of host memory at its peak, where the limits page lets an embedder budget one (INFERRED in the memo, Medium 5; not measured).

A `ToolError`'s text crosses to the guest whole, up to 4,096 characters (`_tool_host.py:190-193`, `:263-266`), so `raise ToolError(os_error)` hands the guest a host path. That is the embedder's choice and the tools page does not say so (READ, the memo's `ToolError` Low).

## Decisions

### 1. Abandoned tool threads are counted per process, with a cap of 64

`process()` gains `tool_threads_abandoned`, written under `tool_threads_lock` beside `tool_threads_running`. A tool call that would be the 65th abandoned thread alive in the process is refused before it starts, as the per-call cap refuses the fifth, with the same `tool_error` frame naming the bound; the count falls when an abandoned thread finally returns. The per-call cap stays. Reason: the per-call cap protects one result, and the process cap protects the host; 64 is sixteen calls' worth at today's per-call cap, enough for a burst and small enough that a host notices long before it degrades. A constant, not a `Defaults` field: a field would change the public API, and a bound the embedder cannot loosen is the safer shape until an embedder asks (constitution §4.15).

### 2. A tool call in a run with no deadline waits at most the session's lifetime, else `_TOOL_WAIT_CEILING`

`_wait`'s `until` is the earliest of the tool's `timeout_s`, the run's deadline and, when both are `None`, the session's lifetime bound or, for a plain `run` with no deadline, a ceiling of 3,600 s named `_TOOL_WAIT_CEILING`. Reason: a wait with no bound is the one shape the tool host may not have (constitution §4.15: every limit has a default), and an hour is long enough that no working tool meets it and short enough that a stuck host function does not hold a call forever.

### 3. The host memory a guest can hold is stated, and measured once

`docs/how-to/limits.md` and `docs/how-to/mounts.md` say that a guest with a writable mount can hold up to `memory_bytes` of linear memory, up to `memory_bytes` of staging, and one more copy of a staged file while the provider is handed it, and that an embedder budgeting host memory for N untrusted guests counts three times `memory_bytes` each. The builder measures the peak once on one machine with one program that stages to the bound and writes a one-page memo beside this specification's landing notes, the number labelled EXECUTED. Reason: the bound follows from three allocations the code names, but the number is a benchmark fact and belongs in a memo, not in a test; a change to the staging design, so that a handed-over file is counted against the staging budget, is a change to the mounts' contract and waits for an embedder who needs it.

### 4. The tools page says what a `ToolError`'s text reaches

`docs/how-to/tools.md` gains one paragraph: the text of a `ToolError` crosses to the guest whole, up to 4,096 characters, so a tool raises one with a message written for the guest and never with a host exception's text, and any other exception crosses as "(internal error)" with the fault kept in the record. Reason: the behaviour is right and chosen; the page did not say it.

### 5. The rows first

- `tests/unit/test_runner_tools.py`: sixteen calls that each abandon four tool threads succeed and the seventeenth call's first tool call is refused with the bound's name in its frame, through a seam on the host's clock (red today); the count falls when an abandoned thread returns and the next call is allowed (red today).
- `tests/unit/test_tools.py`: `_wait` with `timeout_s=None` and no deadline uses the session's lifetime when there is one and `_TOOL_WAIT_CEILING` otherwise, on the stepped clock (red today).
- Every row counts operations and steps the clock; none sleeps for a measurement.

## Intent

After this specification, an embedder that runs untrusted code in many calls knows three numbers and can hold the runner to them: how many abandoned tool threads the process can carry, how long a tool call can wait at most, and how much host memory one guest can hold. The first two are enforced; the third is stated, with its measurement.

## Design

- `src/wasi_python/_process.py`: `tool_threads_abandoned` beside `tool_threads_running` (Decision 1), reset to 0 after a fork as `tool_threads_running` is.
- `src/wasi_python/_tool_host.py`: the process count taken and released around an abandoned thread's life, the refusal before the 65th, `_TOOL_WAIT_CEILING` and the lifetime bound in `_wait` (Decisions 1 and 2).
- `docs/how-to/tools.md`, `docs/how-to/limits.md`, `docs/how-to/mounts.md`: the paragraphs of Decisions 2, 3 and 4; `docs/reference/defaults-and-limits.md`: two rows for the two constants.
- A research memo, `../research/2026-10-XX-what-host-memory-a-guest-can-hold.md`, dated the day it is run, with the one measured peak (Decision 3).
- The news file `../changes/146-the-tool-hosts-bounds-are-the-processs.md`: under Security, "Abandoned tool threads are capped at 64 per process, a tool call in a run with no deadline waits at most the session's lifetime or an hour, and the pages say what host memory a guest can hold and what a `ToolError`'s text reaches."
- The commits, in order: the rows seen failing; the process count and the ceiling; the docs, the memo and the news file.

## Scope

In: the above. Out:

- cancelling an abandoned tool thread: Python offers no safe way, and the embedder's `timeout_s` and its own cancellation remain the tool;
- a `Defaults` field for either bound, which would change the public API: a later specification if an embedder asks;
- counting a handed-over file against the staging budget: a change to the mounts' contract, waiting for an embedder's need;
- the per-call cap's value, which stays 4.

## Acceptance criteria

1. The rows of Decision 5 exist and were seen failing before the change, each named with its failing output in the pull request.
2. `uv run pytest tests/unit/test_runner_tools.py tests/unit/test_tools.py` is green on Linux, macOS and Windows in the pull request's run.
3. No accepted pass is lost, and the tool rows' fuel stays within the ratchet's tolerance.
4. `tests/checks/test_rules.py` is green: the new counter lives in `_process.py` and is reset after a fork, and `_tool_host.py` stays under its ceiling.
5. The four pages say what Decisions 2, 3 and 4 state, `mkdocs build --strict` is green, and the memo of Decision 3 exists with its EXECUTED number.
6. The news file exists and `ci-status` is green.

## Landing notes

Not yet built.
