# 137: the door answers exact bytes, and the audit's other runner notes

- **Status:** **drafted 2026-10-25** from the 0.1.0 security audit (`../reviews/0.1.0-security-audit-2026-10-25.md`, the door, filesystem, shadow and process hardening notes). Not for build until its pre-build review (runner code). Each row is to be written first and seen failing on main's code. The pre-build review may split this specification if it judges the notes too many for one; the natural seams are Decisions 1 to 2 (the door), 3 to 4 (folders), 5 (the poll shadow) and 6 (documents).
- **Date:** 2026-10-25
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/wasi_python/_call.py` (`_door_answer`, `_door`, `_poll_plan`), `_platform.py` (`make_missing`, about ten lines; **1,464 of 1,500 lines**: stacks on 131 if it does not fit), `_private_dirs.py` (one owner check in the sweep), `_zip.py` (`_member_parts`), rows in the unit and hostile-guest check files, `docs/explanation/security-model.md`, `docs/how-to/grants.md`, `CHANGELOG.md`. No `scripts/`, `recipes/`, pins, workflow or artifact byte. Every change tightens.
- **Depends on:** 111 (the file system along the WASI seams) and 113, landed. **127 removes `_poll_plan`'s neighbours** (the `fd_readdir` and `path_rename` shadows) but not `_poll_plan` itself; Decision 5 is unaffected by 127. 129 (output is read from a pipe) touches `_call.py`'s output path, not the door: a rebase, no conflict expected.
- **Research it stands on:** h05's door probes (`0.1.0-security-audit-2026-10-25/agents/h05-door/artifacts/evidence/door_probe.py`, `door_probe_results.json`, the two run logs), h01's and h03's folder notes (`agents/h01-fs-paths/`, `agents/h03-private-dirs/`), h14's `poll_oneoff` comparison against wasmtime (`agents/h14-poll-oneoff/artifacts/evidence/compare_wasmtime.py`), h12's zip-name scan, h08's fork note, h04's read-only-grant note.

## The problem

Nine notes with no boundary violation, each a place where the runner's own check is not the check it means. Grouped by what they touch.

**The door** (`_call.py`, EXECUTED by h05). `_door_answer` (`_call.py:1215-1223`) checks `memoryview(response).nbytes` against `MAX_RESPONSE` and then calls `bytes(response)`. A `bytes` subclass with `__bytes__` returns a different, larger object, so the cap is not enforced on what is written: with the cap patched to 1,000, the guest received 5,000 bytes (`bytes_subclass_over_max`). The same shape lets a subclass's `__len__` run on the guest thread and disagree with the buffer `memory.write` copies: the out-length said 1 while 3,000 bytes were written past a 1-byte allocation (`len_lies`). An answer of 2 GiB or more would be truncated to i32 by wasmtime-py's `Val.i32` when passed to `host_alloc`, while the bound check uses the full length. All three stay inside guest memory, and only the embedder's own host can cause them. `_door`'s `except (wt.Trap, wt.WasmtimeError): raise` (`_call.py:1243-1246`) covers the whole frame, so a host that raises `wasmtime.Trap` ends the call as `trapped` with the host's text (`host_raises_trap`), where the documented outcome for a raising host is a host fault with no text (`security-model.md:28`). Unbounded re-entry of the door from a custom `host_alloc` (reachable only with a module given through `artifacts=`) aborts the process in wasmtime-py's trampoline before `_shared`'s `try` (`reentrant_depth3`); the shipped guest's `host_alloc` is plain `malloc`.

**Folders** (`_platform.py`, `_private_dirs.py`, READ and EXECUTED by h01 and h03). `make_missing` (`_platform.py:387-409`) makes a root's missing components with `os.mkdir(name, dir_fd=fd)` at the umask's mode (0755 under 022) and adopts a `FileExistsError` as "a concurrent call made it"; a missing root named under a folder another user can write (`/tmp` on Linux; macOS's `/private/tmp`, which is not the temp folder there) can be pre-made by that user, who then reads and seeds the guest's files. The sweep (`_private_dirs.py:190`) checks that the lock file is this user's but not that the folder beside it is. `_zip._member_parts` (`_zip.py:108-119`) does not refuse Windows-reserved names, a component ending in a dot or space, or names equal under case folding; the shipped zip holds none, and its input is the checked set, so it matters only for a caller-supplied `artifacts=`.

**The poll shadow** (`_call.py:1082-1137`, EXECUTED by h14, 55 cases against wasmtime). `_poll_plan` says it answers "as wasmtime 49 answers it" but accepts misaligned `in_ptr`, `out_ptr` and `nevents_ptr`, which wasmtime ends the run for, and unknown `subclockflags` bits, which wasmtime answers `EINVAL`; and it reports any descriptor other than 0 to 3 ready with nbytes 1, where wasmtime answers `EBADF` for a descriptor that does not exist or is a folder (a run preopens more than one folder). No memory effect: every write stays in the checked region. The out-pointer bound uses `32*n`, stricter than wasmtime's `32*len(events)`; kept, and said so in a comment, so it is not "fixed" into a weaker bound.

**Documents.** The security model says the runner refuses "a grant or root over any module cache it knows of" (`security-model.md:20`), but a read-only grant over the cache is accepted, as `docs/how-to/grants.md:104` says. The snapshot's zeroed hash secret also fixes pyexpat's salt (`Modules/pyexpat.c:1544-1547` salts each parser from `_Py_HashSecret.expat`), so XML parsing on `snapshot=True` can be flooded as dict keys can (`security-model.md:101` names dicts and sets only). A forked child hangs for good in `wasmtime_module_new` when the parent compiled any module through wasmtime-py **directly**, before the guest runs, so no deadline or Ctrl-C ends it; the runner's fork refusal keys off its own engine only (`_engines._engine` sets `fork_used`).

## Decisions

### 1. The door converts first, then checks, and hands the guest thread exact bytes

`_door_answer` becomes: `data = bytes(response)`; if `type(data) is not bytes`, `data = bytes(memoryview(data))`; if `len(data) > MAX_RESPONSE`, return `None`. What leaves the home thread is an exact `bytes` whose length is its buffer's, so `len(response)` on the guest thread, the `host_alloc` size and the `memory.write` are of one object. `len(response)` is also checked against `MASK32` before `alloc` (a response at or past 2 GiB is a fault, not a truncated size). The frame host's admitted answer takes the same path.

### 2. A raising host is a fault; a nested door is a fault

In `_door.call`, the `except (wt.Trap, wt.WasmtimeError): raise` is narrowed to the `alloc(caller, …)` call alone (a `try` around it inside `frame`), so a host or frame host that raises a wasmtime exception is a `HOST_FAULT` like any other `Exception`, with no text, as documented. A per-call re-entry depth on the call state (not a module global): a door call entered while another is in progress on the same call answers `HOST_FAULT` without reading the frame. The shipped guest never nests; the row uses a stand-in module.

### 3. A made root component is this user's, at 0700

`make_missing` makes each missing component with mode 0700 and, after `os.open(name, _DIR, dir_fd=fd)`, `fstat`s the opened descriptor: a component not owned by the effective uid raises `ValueError` naming it ("a folder on the way to the root was made by another user"). `FileExistsError` is still adopted (a concurrent call of this user), but the ownership check after it is what makes adoption safe. The by-path branch (systems without `dir_fd`) does the same with `os.lstat` after `mkdir`. About ten lines in `_platform.py`; if they do not fit under the ceiling, this decision stacks on 131. The sweep's walk gains `_owned(folder)` beside the lock's check, so a folder another user made at the name of this user's dead lock is never walked.

### 4. The zip's member names are refused by Windows's rules too

`_member_parts` also refuses a component that is a Windows reserved device name (with or without an extension), one that ends in a dot or a space, and a set of members whose components are equal under `casefold()` after NFC, on every system (the data folder is written by the runner, and a name that two systems would read differently is a name the guard should not have to reason about). The shipped zip passes (h12 checked); the rows use a crafted inner archive.

### 5. `_poll_plan` answers as wasmtime does

Before the plan: `in_ptr % 8`, `out_ptr % 8` and `nevents_ptr % 4` nonzero end the run through `_fs_memory._ends`, as the mount shadows do; `flags & ~ABSTIME` answers `EINVAL`. A descriptor subscription is ready only for a descriptor the call's table knows as a file or stdio stream the subscription's direction fits; a number the table does not hold, or a folder, answers `EBADF`, as wasmtime does. The `32*n` bound stays, with its comment. The h14 comparison (`compare_wasmtime.py`) becomes rows in `tests/checks/test_v1_2_hostile_guest.py` beside the existing `poll_oneoff` rows, each asserting the same errno or end as a run against wasmtime's own `poll_oneoff` on a plain grant.

### 6. The documents

- `docs/explanation/security-model.md:20`: "a **writable** grant or root over any module cache it knows of", matching `grants.md:104`.
- `security-model.md`, *Time, randomness and hashing*: the dict-and-set bullet gains "and XML parsed by `xml.etree`, `minidom` or `plistlib`, whose parser salt is the same fixed key".
- `security-model.md`, *Your process's own resources*: the "other code in the same process that uses wasmtime-py directly" bullet gains "a process that compiled a module through wasmtime-py itself must not fork and run a guest in the child: the child waits for the parent's compile pool for good, before any deadline applies".
- `docs/how-to/grants.md` (the `root` section): "a missing root's folders are made for you alone (0700); a folder another user made on the way is refused".
- The CHANGELOG line: "The door hands the guest exactly the bytes it checked, a host that raises a wasmtime exception is a host fault like any other, a missing root's folders are made at 0700 and refused if another user made them, the matplotlib data guard refuses Windows's reserved names, and `poll_oneoff` answers alignment, flag and descriptor errors as wasmtime does."

### 7. The rows first

- Door: the five h05 cases as rows in `tests/unit/test_runner_door.py` (or the existing door unit file): `bytes_subclass_over_max` (the guest receives nothing past the cap), `len_lies` (the out-length equals the bytes written), a 2 GiB-plus length (fault), `host_raises_trap` (host fault, no text in `trapped`), `reentrant_depth3` (fault, the process alive), each seen failing first.
- Folders: a pre-made 0777 component owned by a stand-in uid (the `fstat` injected through the process object) is refused; a made component is 0700; a sweep folder with another owner is not walked; the zip rows of Decision 4.
- Poll: the h14 rows of Decision 5, each red today where the answer differs from wasmtime's.

## Intent

After this specification, what the host answers through the door is checked as the bytes the guest receives, a host that raises anything is a fault with no text, and a nested door call is refused; a root the runner makes is this user's alone; the sweep removes only this user's folders; the matplotlib data guard refuses every name a system would rewrite; and the one WASI call the runner answers itself for every guest answers errors as wasmtime does. The security model says what it means about the cache, XML parsing and forking.

## Design

- `src/wasi_python/_call.py`: `_door_answer` converts then checks, `_door` narrows its re-raise and refuses a nested call (Decisions 1 and 2); `_poll_plan` answers alignment, flags and descriptors as wasmtime does (Decision 5).
- `src/wasi_python/_platform.py`: `make_missing` at 0700 with the owner check (Decision 3), measured against the ceiling first; `src/wasi_python/_private_dirs.py`: the sweep's owner check; `src/wasi_python/_zip.py`: `_member_parts` (Decision 4).
- `tests/unit/test_runner_door.py` and the folder rows; `tests/checks/test_v1_2_hostile_guest.py`: the poll rows re-derived against wasmtime's own answers (Decision 7), first.
- `docs/explanation/security-model.md`, `docs/how-to/grants.md`, `CHANGELOG.md`: Decision 6.
- The commits, in order: the specification with its roadmap line and the rows seen failing; the door; the folders and the zip names; the poll shadow; the documents.

## Scope

In: Decisions 1 to 7. Out: `_write_output`'s copy before the cap (129 changes the output path); judging other host `sys.path` entries as runtime folders (embedder-chosen); a cap on a mount's resolved path length (bounded by `MAX_PATH` per component today); the set-times clamp (127 moves the floor past GHSA-j2g9); the trap-handler re-check during a call (its own specification if the owner wants it).

## Acceptance criteria

1. Every row of Decision 7 green on three systems (platform rows skipped with their reason where a system cannot make the case), each seen failing first on `2cd47507`'s code (output in `build/137/`).
2. The h05 probe (`door_probe.py`, copied to `build/137/`) reports fault or exact bytes for every case on the built tip.
3. `_platform.py` under its ceiling or the Kind line revised to stack on 131; every touched function under 80 lines; no module-level mutable; the test seams on the process object; the rules checks green.
4. `tests/public_api.txt` unchanged; `ruff`, `mypy` clean; no code file names a specification, review, finding or `context/` path.
5. The documents carry Decision 6's text.
6. The release workflow dispatched on the built tip; the Windows legs read for the zip-name and poll rows.

## For the lane

- **Kind:** parallel-safe, runner code, not structural (or stacked on 131 by the Kind line); next wave; shares `_call.py` with 129 (different functions), `_platform.py` with 131 and 135, `docs/explanation/security-model.md` with 132, 134 and 135, `CHANGELOG.md`, `context/roadmap.md`.
- **Claim list** ("137:"): new rows of Decision 7; **changed verdicts:** any existing `poll_oneoff` row whose expected errno moves to wasmtime's is named with its reason; retired none; lost passes none; fuel none expected (the guest's instructions are unchanged; a poll that now ends the run is a hostile-guest row, not a package group); bytes none.
- **Flags:** `--accept "137: the door converts an answer to exact bytes before the cap and hands the guest thread that object, a host that raises a wasmtime exception is a host fault with no text, a nested door call is a fault, a missing root's components are made at 0700 and refused if another user made them, the sweep walks only this user's folders, the data guard refuses Windows's reserved and case-equal names, and poll_oneoff answers misalignment, unknown flags and unknown or folder descriptors as wasmtime does"`, `--accept-judge "137: door, folder, zip-name and poll rows, each seen failing first; the poll rows re-derived against wasmtime's own answers; no existing expectation edited but the poll verdicts the claim list names"`.

## Landing notes

Not yet built. The builder fills this section: the commits, the checks seen failing on main's code first, the fast tier, the branch's release run (its id, every line green on three systems, no growth line), the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

Nine small places where the runner's check was not quite the check it meant, from the door's byte count to a made root's owner, each made exact and held by a row.
