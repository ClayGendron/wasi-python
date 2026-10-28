# 146: The tool host's bounds are the process's

- **Status:** drafted 2026-10-27 from `../research/2026-10-27-a-code-review-of-the-runner-for-production-use.md` (§3); **built 2026-10-27** on `spec/146-the-tool-hosts-bounds-are-the-processs` from `dev`'s `ee72523e`, rebased onto `86fab037`, pushed as pull request #29, reviewed in `../reviews/146-the-tool-hosts-bounds-are-the-processs-pr-2026-10-27.md` (landing notes below); the owner asked for it to be built on 2026-10-27 with the 0.1.2 scope (`../roadmap.md`).
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

Built 2026-10-27 by an agent (Claude Opus 5.5), the builder of this specification, in the worktree `../wasi_python-wt/spec-146`, on `spec/146-the-tool-hosts-bounds-are-the-processs`, first from `898bc091` and rebased onto `ee72523e` (`dev`'s tip, which carries this specification; `git diff --stat 898bc091 ee72523e -- src tests` is empty, EXECUTED). Labels: EXECUTED means I ran it, READ means I read the file cited, INFERRED means my reasoning.

The commits, in order: `21966ca6` the rows; `d515e041` the process count and the ceiling; `54003051` the pages, the memo and the news file; then this section (ids after the rebase onto `86fab037`, which carries the starting-image memo and changes only `context/`; before it, `1b86c5e7`, `697ee544`, `f8d887b0`).

The rows seen failing first (EXECUTED, `build/146/rows-before.txt`, the rows run with `PYTHONPATH` at `ee72523e`'s `src/`, exported by `git archive`): `test_abandoned_tool_threads_are_capped_per_process` and `test_the_process_count_falls_as_an_abandoned_thread_returns` fail with `AttributeError: module 'wasi_python._call' has no attribute '_count_abandoned'`, the seam the final rows hand the bound; `test_a_tool_call_with_no_timeout_and_no_deadline_still_ends` fails with `('cancelled', … 'slow was cancelled') != ('timeout', … 'slow timed out after 3600 s')`, the wait with no bound ended only by the row's fail-safe; `test_reset_after_fork_resets_what_a_child_must_not_inherit` fails with `AttributeError: '_Process' object has no attribute 'tool_threads_abandoned'`. The first draft of the two process rows, which read `process().tool_threads_abandoned` without the seam, failed on their verdicts (EXECUTED, `build/146/rows-process-cap.txt`): the seventeenth call's tool started and was abandoned, `('timeout', True, 'slow timed out after 1 s') != ('timeout', False, 'slow timed out: 64 abandoned tool calls are still running in this process')`, and the count after one thread returned was `0 == 63`. Each row steps a clock and counts reads or threads; none sleeps for a measurement. The tool rows block on events the row sets, and every thread is joined before the row ends.

The code (READ, the diff, `git diff ee72523e -- src`: 39 lines added, 3 removed): `_process.py` holds `tool_threads_abandoned` beside `tool_threads_running`, under `tool_threads_lock`, reset to 0 in `reset_after_fork`. `_call.py`'s `_count_abandoned(delta)` changes it under that lock and answers the count, beside `_count_tool_threads`. `_tool_host.py`'s `_Bounded` is handed it as `abandoned=`, counts a thread in where `_abandon` marks its call and out where the thread's `finally` sees it was abandoned, and answers a tool call `timeout` at once, before its thread starts, while the count is at `_MAX_ABANDONED_IN_PROCESS = 64`, with the message "<name> timed out: 64 abandoned tool calls are still running in this process". `_wait` takes `_TOOL_WAIT_CEILING = 3600.0`, or the `wait_s` it was handed, as the call's wait when the tool has no `timeout_s` and the run has no deadline; the timeout message then reads "<name> timed out after 3600 s". The session's bound is handed `wait_s=state.lifetime_s` and the process count; `run`'s bound the process count.

Criterion 4 (EXECUTED): `uv run pytest tests/checks/test_rules.py` green within the fast tier below. `_tool_host.py` is 1,049 lines, under its ceiling of 1,500 (1,027 before); `_call.py` 1,347; `_process.py` 239. The longest function touched is `_Bounded.__call__`, 33 lines; `_Process.__init__` and `_open_session` keep their allowances. No new lock, no module-level mutable, no platform branch, no change to `tests/public_api.txt`.

Criterion 5 (EXECUTED): `uv run mkdocs build --strict` green. `docs/reference/defaults-and-limits.md` carries both constants as rows of its first table, "tool wait | 3,600, or the session's lifetime | seconds a tool call with no `timeout_s` waits in a run or turn with no deadline" and "abandoned tool threads | 64", each with its row in "How each limit ends a call"; its host-memory paragraph adds the three-times budget. `docs/how-to/tools.md` gains the `ToolError` paragraph (Decision 4), the ceiling (Decision 2) and the process cap (Decision 1); `docs/how-to/limits.md` gains "Budget host memory" and `docs/how-to/mounts.md` the paragraph under "Know the limits" (Decision 3). The memo is `../research/2026-10-27-what-host-memory-a-guest-can-hold.md`: one guest at the default 1 GiB, holding its memory and staging a writable mount's file to the bound, peaked at 3,273,375,744 bytes against an idle call's 262,766,592, so it held 3,010,609,152 bytes, 2.80 GiB, above an idle one (EXECUTED, once, darwin-arm64, the published 0.1.1 set).

The fast tier (EXECUTED, `build/146/fast-tier.log`, `WASI_PYTHON_ARTIFACTS` at the published 0.1.1 set, `uv run pytest -m "not slow" -n 3`, while two other builders ran their own fast tiers, load averages 168 to 195): 2 failed, 3,811 passed, 51 skipped in 862 s; `ratchet vs 1921c3815c: lost 2 · absent 0 · unrun 1 · unrun locally 40 · gained 0 · grew 0`. The two lost passes are `tests/checks/test_v1_2_hostile_guest.py::test_ctrl_c_stops_a_computing_guest[default]` and `[default-turn]`, each "the child did not end within its limit", a wall-clock limit on a child process; run alone by node id they pass, 2 passed in 3.7 s with lost 0 (EXECUTED, `build/146/ctrl-c-alone.txt`), and they passed in this branch's first fast tier (EXECUTED, before the seam moved; 3,812 passed, lost 0, its one failure the import-order check named below). Neither row runs a tool. I read them as the machine's load, not the change (INFERRED); the pull request's run on three systems is the judge of it. `grew 0`: no fuel or bytes grew, so the news file claims no growth; the unit rows add 3 (`units = 3`). The one unrun is `tests/checks/test_rules.py`'s prior-art row, blocked by the clones this worktree does not have. Also EXECUTED: `uv run ruff check src tests`, `uv run ruff format --check src tests` (188 files), `uv run mypy src/wasi_python` (27 files, no issues), `uv run pytest tests/unit/test_runner_tools.py tests/unit/test_tools.py tests/unit/test_process.py tests/unit/test_runner_package.py tests/unit/test_runner_sessions.py` (245 passed), `uv run pytest tests/lint` (9 passed, lost 0), `uv run pytest tests/checks/test_rules.py` (121 passed, 1 skipped, before the seam moved; green again inside the fast tier after).

### Different from the specification, each for a reason

- **The refusal's kind is `timeout`, not `tool_error`.** Decision 1 says the refusal comes "as the per-call cap refuses the fifth, with the same `tool_error` frame". The per-call cap answers `timeout` (READ, `_tool_host.py`, `_Bounded.__call__`; the tools page: "its next tool call is answered `timeout` at once"), so the two halves of the sentence disagree. The build follows the per-call cap, the shape the guest already meets, so a guest sees one answer for both caps (`ToolTimeout`); the message names the process's bound.
- **The process count is handed to the bound, not read by `_tool_host.py`.** The Design puts the take and the release in `_tool_host.py`. The first build imported `process()` there, and `tests/unit/test_runner_package.py::test_the_tool_modules_import_in_their_written_order` refused it: the three tool modules import nothing else of the package at module level, and a late import would need a new entry in that check's `LATE` list, a change to the judge. So the counter's function lives in `_call.py` beside `_count_tool_threads`, and `_Bounded` is handed it as `abandoned=`, as it is handed `count=`; the take and the release, and the refusal, stay in `_tool_host.py`. A bound made with no `abandoned=` counts nothing against the process, as one made with no `count=` counts no running thread; the runner makes two bounds and hands both.
- **Three files beside the Kind line's.** `_call.py` (the counter's function, one keyword), `_sessions.py` (two keywords at the session's bound) and `tests/unit/test_process.py` (the fork reset's row names the new field).
- **The session's lifetime in `_wait` is a second guard.** A session with a lifetime caps every turn's deadline at what is left of it (READ, `_sessions.py`, `_turn_inside`), so in production a tool call in such a session always has a deadline and never reaches `wait_s`. The ceiling of an hour is what bounds a session opened with `lifetime_s=None` and a turn with no deadline, and a plain `run` with `deadline_s=None`. The row drives `wait_s` on the bound itself.
- **The cap is judged when a tool call starts.** A tool call already running is abandoned later, whatever the count is then, so the process can hold more than 64 for a moment: at most 64 plus the tool calls running at once (INFERRED from `_Bounded.__call__`). Holding a slot from the start would count every running tool call, which is the running count's job, not this bound's.
- **One rule slip to record:** the first drafts of the rows, of the fork row and of the code were edited with bare `python3` heredocs before the rule was remembered; every later edit, the measurement and every run went through `uv run`. The measurement program lived in the session's scratch folder, outside the repository; its guest program is quoted whole in the memo.

Pushed as pull request #29. Its first run, `40629373339`, was read by the review, `../reviews/146-the-tool-hosts-bounds-are-the-processs-pr-2026-10-27.md`, before it ended. The review's five Lows for the author are answered in one commit after it: the tools page names a session with no lifetime and both pages say the process cap can be passed by the tool calls already running; the two process rows assert at their start that no tool thread is alive; this Status line and paragraph name the pull request. The push of that commit starts the run that decides criteria 2, 3 and 6, the two Ctrl-C rows among them, and its id is written here at the landing.
