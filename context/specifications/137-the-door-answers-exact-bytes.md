# 137: The door answers exact bytes

- **Status:** built 2026-10-25 on `spec/137-the-door-answers-exact-bytes`, base `f6cd4212`; awaiting its pull-request review. Before: **Reviewed before build 2026-10-25** (`../reviews/137-the-door-answers-exact-bytes-and-the-audits-other-runner-notes-spec-2026-10-25.md`, "fit to build split as 137 (the door: Decisions 1 and 2, with Decision 6's three documentation-only sentences), a folders specification (Decisions 3 and 4, once the Medium's Windows sentence is written), and a poll specification (Decision 5, not fit to build yet: High 1)"): split as the review asked, Decisions 3 to 5 moved to 139 (`139-the-runners-folders-are-this-users-and-the-data-guard-refuses-windows-names.md`) and 140 (`140-the-poll-shadow-answers-as-wasmtime-does.md`), the Lows applied in the Disposition; fit to build. Before: **drafted 2026-10-25** from the 0.1.0 security audit (`../reviews/0.1.0-security-audit-2026-10-25.md`, the door, filesystem, shadow and process hardening notes) as "the door answers exact bytes, and the audit's other runner notes", at the file name the review cites. Each row is to be written first and seen failing on main's code.
- **Date:** 2026-10-25
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/wasi_python/_call.py` (`_door_answer` and `_door`; 1,343 of 1,500 lines, about ten added), rows in `tests/checks/test_v1_2_hostile_guest.py` beside `test_the_door_bounds_every_frame`, three sentences of `docs/explanation/security-model.md`, `CHANGELOG.md`. No `_platform.py`, `_process.py`, `scripts/`, `recipes/`, pins, workflow or artifact byte. Every change tightens.
- **Depends on:** nothing in flight. It is independent of 139 and 140 (the split's other two halves) and of 131 (the `_platform.py` split): it does not touch `_platform.py`. Landed and unchanged: the door and its cap (`MAX_RESPONSE`, held by `test_the_door_bounds_every_frame`), and the home thread the host runs on (078). It shares `_call.py` with 140 (140 changes `_Call.__init__`'s `self.poll` line, the line after `self.door`, which 137 leaves as it is: a rebase names it if they meet) and with 129 (the output path and `_instance`, not the door). 127 does not touch the door.
- **Research it stands on:** h05's door probes (`../reviews/0.1.0-security-audit-2026-10-25/agents/h05-door/artifacts/evidence/door_probe.py`, `door_probe_results.json`, `door_probe_output_run1.txt` and `door_probe_output_run2.txt`), h08's fork note, h04's read-only-grant note, and the pre-build review's door probe (`build/137-review/door-probe.txt`, EXECUTED there).

## The problem

Five notes with no boundary violation, each a place where the door's own check is not the check it means, and three sentences of the security model that say less or more than the runner does.

**The door** (`_call.py`, EXECUTED by h05 and again by the pre-build review). `_door_answer` (`_call.py:1215-1223`) checks `memoryview(response).nbytes` against `MAX_RESPONSE` and then calls `bytes(response)`. A `bytes` subclass with `__bytes__` returns a different, larger object, so the cap is not enforced on what is written: with the cap patched to 1,000, the guest received 5,000 bytes (`bytes_subclass_over_max`). The same shape lets a subclass's `__len__` run on the guest thread and disagree with the buffer `memory.write` copies: a `__bytes__` that returns a subclass whose `__len__` lies made the out-length say 1 while 3,000 bytes were written past a 1-byte allocation (`len_lies`). On Python 3.11 and later a plain subclass with a lying `__len__` and no `__bytes__` is already copied to exact `bytes` by `bytes()`, so the row keeps h05's shape (EXECUTED by the review). Through the same `__bytes__` path an answer of 2 GiB or more could reach `host_alloc`, whose size wasmtime-py's `Val.i32` truncates, while the bound check uses the full length (READ, the audit's reading of the code; not run, it needs a 2 GiB answer). All of these stay inside guest memory, and only the embedder's own host can cause them.

**A raising host and a nested door** (READ, `_call.py:1240-1246`). `_door`'s `except (wt.Trap, wt.WasmtimeError): raise` covers the whole frame, so a host that raises `wasmtime.Trap` ends the call as `trapped` with the host's text (`host_raises_trap`), where the documented outcome for a raising host is a host fault with no text (`security-model.md:28`). This is an outcome the embedder sees, not a channel to the guest: the guest gets -2 or its run ends, and the text reaches `Done.trapped` (READ, the review). Unbounded re-entry of the door from a custom `host_alloc` (reachable only with a module given through `artifacts=`) aborts the process in wasmtime-py's trampoline before `_shared`'s `try` (h05's unbounded run 1, exit 134; `reentrant_depth3` returned normally, exit 3 with four host calls; READ, h05's `door_probe_results.json` and run logs). The shipped guest's `host_alloc` is plain `malloc`.

**Documents** (READ). The security model says the runner refuses "a grant or root over any module cache it knows of" (`security-model.md:20`), but a read-only grant over the cache is accepted, as `docs/how-to/grants.md:104` says. The snapshot's zeroed hash secret also fixes pyexpat's salt (READ, `Modules/pyexpat.c:1544-1548` in the pinned 3.15.0 source: each parser is salted from `_Py_HashSecret.expat`), so XML parsing on `snapshot=True` can be flooded as dict keys can (`security-model.md:101` names dicts and sets only). A forked child hangs for good in `wasmtime_module_new` when the parent compiled any module through wasmtime-py **directly**, before the guest runs, so no deadline or Ctrl-C ends it; the runner's fork refusal keys off its own engine only (`_engines._engine` sets `fork_used`; READ, h08).

## Decisions

### 1. The door checks the buffer, converts, and checks the exact bytes again

`_door_answer` keeps `if memoryview(response).nbytes > MAX_RESPONSE: return None` as the first test, then converts: `data = bytes(response)`; if `type(data) is not bytes`, `data = bytes(memoryview(data))`; then `len(data) > MAX_RESPONSE` again on the exact bytes returns `None`. Reason: the first test refuses an over-cap buffer before any copy, so a 1.9 GiB `bytearray` is not doubled before it is refused (today's comment, "checked in bytes, before the copy", stays true); the second holds the cap on the object that is written, whatever a subclass's `__bytes__` returned. What leaves the home thread is an exact `bytes` whose length is its buffer's, so `len(response)` on the guest thread, the `host_alloc` size and the `memory.write` are of one object (READ, wasmtime-py `_memory.py:122-124`: `memory.write` copies with `bytearray(value)` and writes `len` of that copy). The cap, `0x7FFFFFFF`, is below 2 GiB, so on exact bytes it also keeps every length within a signed i32 and wasmtime-py never truncates one; no second test. The frame host's admitted answer takes the same path. Over the cap the answer is `None`, so `HOST_FAULT` (-2), and the guest's `_host.call` raises `OSError`, the fault today's "response too large" row already sees (READ, `test_v1_2_hostile_guest.py:250-273`): no new error type.

### 2. A raising host is a fault; a nested door is a fault

In `_door.call`, the `except (wt.Trap, wt.WasmtimeError): raise` is narrowed to the `alloc(caller, …)` call alone (a `try` around it inside `frame`), so a host or frame host that raises a wasmtime exception is a `HOST_FAULT` like any other `Exception`, with no text, as documented. Reason: a trap or exit inside `host_alloc` is the guest's and must reach the shared function, but a wasmtime exception the host raises is the host's, and the documented outcome for the host is one. A per-call re-entry depth lives in `_door`'s closure, which is built once per `_Call` (READ, `_call.py:682`), so it is per call and not a module global: a door call entered while another is in progress on the same call answers `HOST_FAULT` without reading the frame. Reason: the nested call is the one that aborts the process today, and the shipped guest never nests, so a refusal costs no working program. After this, only `alloc`'s wasmtime errors pass the door, and `KeyboardInterrupt`, `SystemExit` and the home's `_Stopped` still pass by design (READ, `runner.py:239`).

### 3. The documents

Three sentences that need no row, landed with the door so the security model is read once. Reason: each is a correction of what the page claims, and none waits on a behaviour change.

- `docs/explanation/security-model.md:20`: "a **writable** grant or root over any module cache it knows of", matching `grants.md:104`.
- `security-model.md`, *Time, randomness and hashing*: the dict-and-set bullet gains "and XML parsed by Python's expat parsers (`xml.etree`, `xml.dom.minidom`, `xml.sax`, `plistlib`, `xmlrpc`), whose parser salt is the same fixed key".
- `security-model.md`, *Your process's own resources*: the "other code in the same process that uses wasmtime-py directly" bullet gains "a process that compiled a module through wasmtime-py itself must not fork and run a guest in the child: the child waits for the parent's compile pool for good, before any deadline applies".
- The CHANGELOG line: "The door hands the guest exactly the bytes it checked, a host that raises a wasmtime exception is a host fault like any other, and a nested door call is a fault; the security model says a writable grant over the module cache is refused, names XML parsing beside dict keys under the snapshot's fixed key, and says a process that used wasmtime-py directly must not fork and run a guest."

### 4. The rows first

All in `tests/checks/test_v1_2_hostile_guest.py`, beside `test_the_door_bounds_every_frame`, which already patches `MAX_RESPONSE`. Each is seen failing first on `2cd47507`'s code but the one guard row.

- `bytes_subclass_over_max`: the guest receives nothing past the cap (a fault); today 5,000 bytes pass a cap of 1,000 (EXECUTED by the review).
- `len_lies`, in h05's shape (a `__bytes__` that returns a subclass with a lying `__len__`): the out-length equals the bytes written; today a `len` of 1 over a 3,000-byte buffer (EXECUTED by the review).
- `MAX_RESPONSE < 2**31`, asserted (a guard row, not one seen failing).
- `host_raises_trap`: a host fault, no text in `trapped`; today trapped "from the host" (READ, `door_probe_results.json`).
- `reentrant_depth3`: the nested call is a fault and the call ends normally; today the nested calls are answered (exit 3, four host calls; READ, `door_probe_results.json`).
- `reentrant_unbounded`, in a subprocess: today the process aborts (exit 134); after, the nested call is a fault and the process exits normally.

## Intent

After this specification, what the host answers through the door is checked as the bytes the guest receives, a host that raises anything is a fault with no text, and a nested door call is refused. The security model says what it means about the cache, XML parsing and forking.

## Design

- `src/wasi_python/_call.py`: `_door_answer` checks, converts and checks again (Decision 1); `_door` narrows its re-raise to `alloc` and refuses a nested call by a depth in its closure (Decision 2). `_door` is 57 lines today and about 67 after, under 80 (EXECUTED, `ast`, by the review; INFERRED, the count).
- `tests/checks/test_v1_2_hostile_guest.py`: the rows of Decision 4, first.
- `docs/explanation/security-model.md`, `CHANGELOG.md`: Decision 3.
- The commits, in order: the rows seen failing; the door; the documents.

## Scope

In: Decisions 1 to 4. Out: the folders and the data guard's names (139); the poll shadow (140); `_write_output`'s copy before the cap (129 changes the output path); judging other host `sys.path` entries as runtime folders (embedder-chosen); a cap on a mount's resolved path length (bounded by `MAX_PATH` per component today); the set-times clamp (127 moves the floor past GHSA-j2g9); the trap-handler re-check during a call (its own specification if the owner wants it).

## Acceptance criteria

1. Every row of Decision 4 green on three systems, each but the guard row seen failing first on `2cd47507`'s code (output in `build/137/`).
2. The h05 probe (`door_probe.py`, copied to `build/137/`) reports a fault or exact bytes for every case on the built tip.
3. Every touched function under 80 lines; no module-level mutable (the depth is in `_door`'s closure); the rules checks green.
4. `tests/public_api.txt` unchanged; `ruff`, `mypy` clean; no code file names a specification, review, finding or `context/` path.
5. The security model carries Decision 3's three sentences.
6. The release workflow dispatched on the built tip, every line read on three systems.

## For the lane

- **Kind:** parallel-safe, runner code, not structural; next wave; shares `_call.py` with 140 (adjacent lines in `_Call.__init__`) and 129 (different functions), `docs/explanation/security-model.md` with 132, 134 and 135, `CHANGELOG.md`, `context/roadmap.md`.
- **News file:** `context/changes/137-the-door-answers-exact-bytes.md` once 138's news files are in use, holding the CHANGELOG line of Decision 3 and the claim block below; until then the line goes under the unreleased section.
- **Claim list** ("137:"): new the rows of Decision 4, ten node ids in `tests/checks/test_v1_2_hostile_guest.py`: `test_the_door_writes_exactly_the_bytes_it_checked[a bytes subclass past the cap]`, `[a bytearray subclass past the cap]`, `[a len that lies]`, `[a bytearray]`, `[a memoryview of ints]`; `test_the_door_cap_keeps_every_length_a_signed_i32`; `test_a_host_that_raises_a_wasmtime_exception_is_a_host_fault[Trap]`, `[WasmtimeError]`; `test_a_nested_door_call_is_a_host_fault`; `test_an_unbounded_nested_door_call_leaves_the_process_running`; changed verdicts none; retired none; lost passes none; fuel none expected (the guest's instructions are unchanged); bytes none.
- **Flags:** `--accept "137: the door checks an answer's buffer, converts it to exact bytes and checks the cap again before the guest thread writes it, a host that raises a wasmtime exception is a host fault with no text, and a nested door call is a fault"`, `--accept-judge "137: the door rows beside test_the_door_bounds_every_frame, each seen failing first but the cap's guard row and the plain bytearray and memoryview cases; no existing expectation edited"`. The orchestrator accepts locally until 138's step 3, with both flags as written.

## Disposition of the pre-build review

`../reviews/137-the-door-answers-exact-bytes-and-the-audits-other-runner-notes-spec-2026-10-25.md`; the author's answers, 2026-10-25, for the findings this specification holds. The split and the others are in the review's Disposition.

1. **Low 3, the copy before the cap:** fixed in Decision 1 with the review's text: the `nbytes` test first, then the conversion, then `len` again on the exact bytes.
2. **Low 4, the 2 GiB sentence and row:** fixed: Decision 1 carries the review's `0x7FFFFFFF` sentence in place of the `MASK32` one, and Decision 4's 2 GiB-plus row is the `MAX_RESPONSE < 2**31` guard row.
3. **Low 5, the re-entry evidence:** fixed in The problem (h05's unbounded run 1, exit 134; `reentrant_depth3` returned normally) and Decision 4 (`reentrant_unbounded` in a subprocess).
4. **Low 8, the door rows' file:** fixed: Decision 4 puts the rows in `tests/checks/test_v1_2_hostile_guest.py` beside `test_the_door_bounds_every_frame`; the nonexistent `tests/unit/test_runner_door.py` is gone. The finding's other parts went to 139 and 140.
5. **Low 10, the XML parsers:** fixed in Decision 3 with the review's text.

## Landing notes

Built 2026-10-25 by an agent (Claude, session `https://claude.ai/code/session_01FZg7sj9WydizfDe18oakTT`) on `spec/137-the-door-answers-exact-bytes`, base `f6cd4212` (its `src/` is `2cd47507`'s: the rows failed on 0.1.0's door). Three commits, in the Design's order: the rows seen failing; the door; the documents.

**Files.** `src/wasi_python/_call.py` (`_door_answer` checks `nbytes`, converts to exact `bytes`, checks `len` again; `_GuestStop` carries a trap or exit inside `host_alloc` past the door's `except Exception`; `_door` refuses a nested call by a depth in its closure; `_door` 70 lines, `_door_answer` 17, `frame` 34; the module 1,372 of 1,500). `tests/checks/test_v1_2_hostile_guest.py` (the rows, after `test_the_door_bounds_every_frame`). `docs/explanation/security-model.md` (Decision 3's three sentences). `CHANGELOG.md` (the line under `### Security` in a new `## 0.1.1 — unreleased` section, the shape 132's branch uses, by hand under AGENTS.md's transitional paragraph). `tests/public_api.txt` unchanged; `SECURITY.md` needs no change (it names the door as a boundary and says nothing of a host's exceptions).

**The rows, each seen failing first** (`build/137/rows-before.txt`, the run on `abb1dc24`, today's door; green after in `build/137/rows-after.txt`, 16 passed with the existing door rows and `test_a_large_response_is_a_host_fault`):

- `test_the_door_writes_exactly_the_bytes_it_checked[a bytes subclass past the cap]`: `exit_code=5000` at a cap of 4,000 (h05's `bytes_subclass_over_max`); after, -2.
- `…[a bytearray subclass past the cap]`: `exit_code=5000` (the review's `bytearray_bytes_big`); after, -2.
- `…[a len that lies]`, h05's shape: `exit_code=1003000`, that is 3,000 bytes written under an out-length of 1; after, 3,000.
- `…[a bytearray]` and `…[a memoryview of ints]`: guard cases, green on today's code as the review's probe found (a memoryview's answer is its 1,200 bytes, not its 300 items).
- `test_the_door_cap_keeps_every_length_a_signed_i32`: the guard row, green on today's code.
- `test_a_host_that_raises_a_wasmtime_exception_is_a_host_fault[Trap]` and `[WasmtimeError]`: `trapped='from the host'`; after, `(-2, None)`, the text nowhere in the result.
- `test_a_nested_door_call_is_a_host_fault`: `exit_code=0` with 4 host calls (h05's `reentrant_depth3`); after, `(-2, None, 1)`.
- `test_an_unbounded_nested_door_call_leaves_the_process_running`: the child aborted, return code -6 (SIGABRT, h05's exit 134), its stderr wasmtime-py's `RecursionError` in the trampoline; after, return code 0 and `-2 None 1`.

**Criterion 2.** h05's `door_probe.py`, copied to `build/137/`, before (`build/137/door-probe-before.txt`) and after (`build/137/door-probe-after.txt`): after, `host_raises_trap` is -2 with no text, `bytes_subclass_over_max` 102 (the fault), `len_lies` 3,000 (exact bytes), `reentrant_depth3` one host call; every other case as before; the unbounded case stays commented out in the probe, as h05 left it, and is the subprocess row above.

**Validation.** `uv run ruff check src tests` and `uv run ruff format --check src tests` clean; `uv run mypy` "no issues found in 24 source files"; `uv run pytest tests/checks/test_rules.py -q -p no:cacheprovider` 73 passed, 1 skipped; `tests/unit/test_runner_tools.py`, `test_runner_cancel.py`, `test_guest.py` and `test_v1_4_embedding.py::test_ctrl_c_before_a_cancel_in_the_door` 82 passed, 4 skipped. The fast tier, `uv run pytest -m "not slow" -n 2 -q -p no:cacheprovider` on `5eab0425` (`build/137/fast-tier.txt`), at a load average near 230 on a shared machine: "1 failed, 3142 passed, 51 skipped in 2117.75s"; "ratchet vs d33f0383c6: lost 1 · absent 0 · unrun 0 · unrun locally 40 · gained 10 · grew 0". The ten gained are the new rows. The one lost is `tests/checks/test_v1_4_embedding.py::test_concurrent_calls_get_their_own_results`, its child past the 120 s fail-safe (`subprocess.TimeoutExpired`, 800 door-calling runs on eight threads); alone by node id on the same tree it passed in 41.96 s (`build/137/concurrent-rerun.txt`). It is the machine's load, not the door: the door's depth is per call, and the rows and the door's unit tests are green. The lane's own run is the check that it holds.

**Self-check** (`../reviews/README.md`, until the template exists). Author: the session above. Every new check seen failing first: the seven above, each with its output; the guard row and the two guard cases say they guard what already held. Windows legs read: not yet; no release run or pull-request run on this branch; the run id goes here when the pull request runs under `ci-status`. Gaps: none opened or closed. News file: none yet (138's step 3); the CHANGELOG line is in by hand.

**Run.** None yet: the pull request's run id is added here when it runs under `ci-status`.

## One line

The door checks what the guest will receive, not what the host said it sent: an answer is made exact bytes and capped, a host's own wasmtime exception is a fault, a nested call is refused, and the security model says what it means about the cache, XML and forking.
