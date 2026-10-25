# 140: The poll shadow answers as wasmtime does

- **Status:** **drafted 2026-10-25** from the split of 137 by its pre-build review (`../reviews/137-the-door-answers-exact-bytes-and-the-audits-other-runner-notes-spec-2026-10-25.md`, which read this as 137's Decision 5 and found its High 1 here); not fit to build until its own pre-build review. High 1's mechanism and Low 9's error handling are written in, with the review's text, as Decisions 3 and 4; the review's own probe of this half was a reading, not a run. Each row is to be written first and seen failing on main's code.
- **Date:** 2026-10-25
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/wasi_python/_call.py` (`_poll_plan`, `_poll_oneoff`, and `_Call.__init__`'s one `self.poll` line; 1,343 of 1,500 lines, about 25 added), `src/wasi_python/_fs_table.py` (one method that reads `table` and `held` for a descriptor's kind; 681 lines), rows in `tests/checks/test_v1_2_hostile_guest.py` and `tests/unit/test_runner_waits.py`, the stand-in `kind` in `tests/unit/test_runner_sessions.py`'s poll helper, `CHANGELOG.md`. No `_platform.py`, `scripts/`, `recipes/`, pins, workflow or artifact byte. No private wasmtime-py name is added: the runner never asks wasmtime a descriptor's kind (Decision 3).
- **Depends on:** nothing in flight. It is independent of 137 and 139 (the split's other two halves) and of 131: it does not touch `_platform.py`. Landed and unchanged: the poll shadow (`_poll_plan`, `_poll_oneoff`), the counted calls that keep `held` (068: `path_open`, `fd_close` and `fd_renumber` are shadowed on every call, with mounts or without; READ, `_fs_table.py:13-20` and `_fs_memory.py:78-81`), 111 and 113. 127 removes `_poll_plan`'s neighbours (the `fd_readdir` and `path_rename` shadows) but keeps the counted calls (READ, 127's Decisions 2 and 3c: the guard linker keeps the three counted calls as `_counted_linker`), so `held` is still kept after it; 127 moves the pin to wasmtime 50, and the rows of Decision 5 are derived against the wasmtime main pins when this is built (INFERRED: h14 compared against wasmtime 49). It shares `_call.py` with 137 (the `self.door` line, adjacent to `self.poll`) and 129, `CHANGELOG.md` and `context/roadmap.md`.
- **Research it stands on:** h14's `poll_oneoff` comparison against wasmtime, 55 cases (`../reviews/0.1.0-security-audit-2026-10-25/agents/h14-poll-oneoff/artifacts/evidence/compare_wasmtime.py`, `compare_wasmtime.json`, `compare_wasmtime.log`), and the pre-build review of 137 (its High 1 and Low 9).

## The problem

`_poll_plan` (`_call.py:1082-1114`) says it answers "as wasmtime 49 answers it", and in four ways it does not (EXECUTED by h14, 55 cases against wasmtime; READ here).

- It accepts misaligned `in_ptr`, `out_ptr` and `nevents_ptr`, which wasmtime ends the run for.
- It accepts unknown `subclockflags` bits, which wasmtime answers `EINVAL`.
- It reports any descriptor other than 0 to 3 ready with nbytes 1, where wasmtime answers `EBADF` for a descriptor that does not exist or is a folder; a run preopens more than one folder, so 3 is not the only preopen.
- `_poll_oneoff.call`'s `except Exception: return EINVAL` (`_call.py:1171-1172`) would swallow a `WasmtimeError` from `_fs_memory._ends` into `EINVAL`, so the alignment fix cannot be written inside today's handler (READ, the review's Low 9).

No memory effect: every write stays in the checked region. The out-pointer bound uses `32*n`, stricter than wasmtime's `32*len(events)`; kept. And h14 shows wasmtime ending the run for an out-pointer with no room, where the shadow answers `EFAULT` (READ, `compare_wasmtime.json`): a difference this specification keeps (Decision 4).

The draft's descriptor rule, "a number the table does not hold, or a folder, answers `EBADF`", had no way to know wasmtime's own descriptors (READ, the review's High 1). The call's table holds only the mounts' entries (`table`) and the numbers of what wasmtime opened (`held`), never their kind (`_fs_table.py:97-134`). Every file the guest opens on a plain grant or on the zip is wasmtime's descriptor, so the rule as written would answer `EBADF` for every such file, where wasmtime and today's shadow both answer ready: a guest that opens `/data/x.txt` on a read-only grant and polls it for reading would get `EBADF` on a path that works today.

## Decisions

### 1. Misaligned pointers end the run

Before the plan, `in_ptr % 8`, `out_ptr % 8` and `nevents_ptr % 4` nonzero end the run through `_fs_memory._ends`, as the mount shadows do. Reason: wasmtime ends the run for them (h14), and `_ends` is the runner's one way to give a guest wasmtime's ABI end.

### 2. Unknown clock flags are `EINVAL`

`flags & ~ABSTIME` nonzero answers `EINVAL`. Reason: wasmtime answers it so (h14), and today's shadow ignores the bits.

### 3. A descriptor is answered from what the runner knows

A descriptor subscription is answered from what the runner knows: 0 to 2 as today; a preopen's number (3 up to 3 plus the call's preopens) and a mount's folder `EBADF`; a mount's file, or a number in the table's `held`, ready; any other number `EBADF`. `_poll_plan` takes a `kind(fd)` argument, so the unit rows stay pure. A folder the guest opened through `path_open` is held, and is answered ready where wasmtime answers `EBADF`: a kept difference, said in the docstring, since the runner does not ask wasmtime a descriptor's kind.

Reason: the call already knows every number the guest can hold, by the counted calls, and asking wasmtime a held number's kind would mean a forward of `fd_fdstat_get`, which writes into guest memory, or tracking `path_open`'s flags; neither is worth one poll answer for a folder, which no working program polls. `held` is read before the preopen numbers, so a file the guest renumbered onto a preopen's number (`_renumbered` moves it into `held`, READ, `_fs_table.py:594-599`) is ready, as wasmtime answers it (INFERRED; its own pre-build review judges the order). The `kind` comes from one `_Files` method in `_fs_table.py`, and `_poll_oneoff` takes it as a required keyword argument, built where `_Call.__init__` builds `self.poll`; the call's preopen count reaches it from the instance's preopens, mount placeholders included (INFERRED: the builder confirms where that count is first known).

### 4. The poll's own errors, and the differences kept

`call` re-raises a `WasmtimeError` before its `except Exception`, and records the fuel as `_Files.__call__` does for an ABI error; the bounds' `EFAULT` (wasmtime ends the run) and the `32*n` bound are kept differences, named in the docstring and asserted as the shadow's own answers. Reason: the re-raise goes to the shared function, which records it as the call's stop, as every `_ends` error does (READ, `_fs_memory.py:185-193`); the fuel then is the guest's, as for a mount shadow's ABI error (READ, `_fs_table.py:268-278`). The two bounds are kept because each lets through no more than wasmtime does and no write differs; a row asserts each, so neither is "fixed" into a weaker bound later.

### 5. The rows first

- Hostile guest, in `tests/checks/test_v1_2_hostile_guest.py` beside the existing `poll_oneoff` rows: the h14 cases where the answer differs from wasmtime's, each asserting the same errno or end as a run against wasmtime's own `poll_oneoff` on a plain grant, each red today; a file opened on a plain grant and polled for reading, ready on both (the row High 1 asked for, green today and kept green); the two kept differences, each asserting the shadow's own answer; and a folder opened through `path_open`, ready, asserted as the shadow's kept answer.
- Unit, in `tests/unit/test_runner_waits.py`: `_poll_plan` with a stand-in `kind`: an unknown number `EBADF`, a held number ready, a preopen's number past 3 `EBADF`, a mount's folder `EBADF`, a mount's file ready, unknown flag bits `EINVAL`.
- `tests/unit/test_runner_waits.py::test_descriptors_follow_wasmtime`: fd 9 moves from ready to `EBADF`, as wasmtime answers it (a changed verdict, named in the claim list).

## Intent

After this specification, the one WASI call the runner answers itself for every guest answers misalignment, unknown flags and descriptors it does not hold as wasmtime does, and says in its docstring the three places it knowingly differs: a folder the guest opened, the out-pointer's `EFAULT`, and the `32*n` bound.

## Design

- `src/wasi_python/_call.py`: `_poll_plan(raw, n, realtime_ns, monotonic_ns, kind)` answers flags and descriptors (Decisions 2 and 3); `_poll_oneoff(origin_ns, waits, …, kind=…)` checks alignment first, re-raises a `WasmtimeError` and records the fuel (Decisions 1 and 4); `_Call.__init__` builds the poll with the call's `kind`. `_poll_plan` is 32 lines today and `_poll_oneoff` 36 (EXECUTED, `ast`, by the review), each under 80 after (INFERRED).
- `src/wasi_python/_fs_table.py`: the `kind` method, reading `table` and `held` and the preopen count.
- The rows of Decision 5, first; `CHANGELOG.md`: "`poll_oneoff` answers misaligned pointers, unknown clock flags, and descriptors the guest does not hold or that are folders as wasmtime does."
- The commits, in order: the rows seen failing; the poll; the CHANGELOG line.

## Scope

In: Decisions 1 to 5. Out: asking wasmtime a held descriptor's kind (Decision 3's kept difference); nbytes other than wasmtime's for a ready file (the rows assert wasmtime's own); the door (137); the folders and the data guard's names (139).

## Acceptance criteria

1. Every row of Decision 5 green on three systems, each red row seen failing first on `2cd47507`'s code (output in `build/140/`).
2. `compare_wasmtime.py`, copied to `build/140/`, shows no difference on the built tip but the three kept, each named in `_poll_plan`'s or `_poll_oneoff`'s docstring.
3. Every touched function under 80 lines; no module-level mutable; no private wasmtime-py name outside `_wasmtime_ffi.py`; the rules checks green.
4. `tests/public_api.txt` unchanged; `ruff`, `mypy` clean; no code file names a specification, review, finding or `context/` path.
5. The release workflow dispatched on the built tip; the Windows legs read for the poll rows.

## For the lane

- **Kind:** parallel-safe, runner code, not structural; a wave after its own pre-build review; shares `_call.py` with 137 and 129, `CHANGELOG.md`, `context/roadmap.md`.
- **News file:** `context/changes/140-the-poll-shadow-answers-as-wasmtime-does.md` once 138's news files are in use, holding Design's CHANGELOG line and the claim block below; until then the line goes under the unreleased section.
- **Claim list** ("140:"): new the rows of Decision 5; **changed verdicts:** `tests/unit/test_runner_waits.py::test_descriptors_follow_wasmtime` (fd 9 moves from ready to `EBADF`, as wasmtime answers it), and any existing `poll_oneoff` row whose expected errno moves to wasmtime's, named with its reason; retired none; lost passes none; fuel none expected (a poll that now ends the run is a hostile-guest row, not a package group); bytes none.
- **Flags:** `--accept "140: poll_oneoff ends the run for misaligned pointers, answers unknown clock flags EINVAL, and answers a descriptor the call does not hold, a preopen or a mount's folder EBADF, as wasmtime does"`, `--accept-judge "140: poll rows re-derived against wasmtime's own answers, each red one seen failing first; test_descriptors_follow_wasmtime's fd 9 moves to EBADF; the kept differences asserted as the shadow's own"`.

## Landing notes

Not yet built. The builder fills this section: the commits, the checks seen failing on main's code first, the fast tier, the comparison's output, the branch's release run (its id, every line green on three systems, no growth line), the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

The poll the runner answers itself for every guest refuses what wasmtime refuses, from a misaligned pointer to a descriptor it does not hold, and names the three places it knowingly differs.
