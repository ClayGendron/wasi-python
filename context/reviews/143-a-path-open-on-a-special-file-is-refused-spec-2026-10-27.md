# Review of 143 — A path_open on a special file is refused

- **Date:** 2026-10-27
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** the specification as drafted, `context/specifications/143-a-path-open-on-a-special-file-is-refused.md` at `daf007b9` on `spec/143-a-path-open-on-a-special-file-is-refused` (based on `898bc091`, whose `src/` is `dev`'s), with the code it changes: `_fs_paths.py` (`_path_open`, the forward branch), `_fs_table.py` (`forward`, `_Files`, `_gate`), `_fs_memory.py`, `_call.py` (`_shared`, `_epoch_answer`, `_counted_linker`, `_fuel_used`), `mounts.py`, the two docs lines it edits, and the rows' homes (`tests/unit/test_runner_grants.py`, `tests/checks/test_v1_2_hostile_guest.py`, `tests/harness/files.py`, `tests/harness/needs.py`, `tests/harness/plugin.py`)
- **Run:** none (a pre-build review). Checklist items 1 and 2 (the pull request's run, the builder's self-check) do not apply.
- **Re-ran:**
  - `PYTHONPATH=src uv run python build/143-review/probe.py` (wasmtime-py 50.0.1, macOS arm64; a FIFO, a Unix socket, a file, a folder and links planted in a writable grant, driven through `harness.files.Counted`, the raw module on the counted linker) → exit 0, `probe.log`. Kept under the worktree's ignored `build/143-review/`, not committed.
  - `PYTHONPATH=src uv run python build/143-review/epoch.py` (a look forwarded through the runner's trampoline after the call's deadline has passed, with the runner's epoch callback on the store) → exit 0, `epoch.log`.
  - `PYTHONPATH=src uv run python build/143-review/skipped.py` (the opens Decision 3 forwards without a look, each on a FIFO, in a daemon thread joined for at most 5 s as a fail-safe) → exit 0, `skipped.log`: none waited.
  - `PYTHONPATH=src uv run python build/143-review/layout.py <main tree>/build/artifacts/python.wasm` (the guest's data segments and globals, by `tests/harness/wasm.py` and a reader of the global section) → exit 0, `layout.log`.
  - `uv run python tests/harness/wrap.py --check` on the specification after my edits → exit 0; `uv run python -m pytest tests/lint -q -p no:cacheprovider` after this file (the worktree's `.venv/bin/pytest` carries another path's shebang, so `python -m pytest`).
  - No fast tier, no shard, no full judge.
- **Time box:** 45 minutes (reviewed before it is built, with probes); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

## The key design: a forwarded look on the open's own descriptor

Sound against a hostile guest. The look is wasmtime's own `path_filestat_get`, forwarded through the trampoline the forward branch already uses, with the open's descriptor, lookup flags, path pointer and length; it resolves the name in wasmtime's sandbox, exactly as the open will, and tells the guest nothing its own unshadowed `path_filestat_get` does not.

- Filetypes (EXECUTED, `probe.log`): a FIFO answers 0 with and without follow; a Unix socket answers 0; a file 4; a folder 3; a link to the FIFO answers 7 without follow and 0 with it; a link to the file 7 and 4. The author's claims hold on wasmtime-py 50.0.1.
- Following as the open follows is the right call (Decision 5). A look that never followed would answer 7 for a link to a FIFO, forward the open, and the open, which follows, would wait (EXECUTED, `probe.log` for the 7; the wait is the author's `opens.log`). A guest on a writable grant can make that link itself with `path_symlink`, which is wasmtime's own; the specification's refinement closes that. A hard link a guest makes with `path_link` is itself a FIFO, filetype 0, refused (INFERRED).
- The look's errno against the open's, on names that are not special (EXECUTED, `probe.log`): `missing` 44/44, `file/x` 54/54, `file/` 54/54, `../x` 63/63, `/etc` 63/63, a link out of the grant 63/63, `dir/../../x` 63/63, the empty path 44/44, `fifo/` 54/54, an unknown base 8/8. One differs: a base that is a file answers `EBADF` (8) to the look and `ENOTDIR` (54) to the open. It does not matter: any errno from the look forwards the open, so the guest gets wasmtime's own answer in its own order. With `O_CREAT` on a new name the look answers 44 and the forwarded open creates it (0).
- Errno order (READ, `p1.rs:2156-2210`, `filesystem.rs:935-1009`; EXECUTED, `skipped.log`): wasmtime's checks before its host open are the flag conversion (an undefined bit ends the run), the base's kind, the path's read, the sync flags (58), `O_DIRECTORY` with a create (28), `O_CREAT|O_EXCL` (20, at the host's create-new) and the read-only grant's write (63). Decision 3 leaves every one to wasmtime but the last, which it names; finding 2 widens the name to `ENOTDIR`, and finding 3 adds `out`, which wasmtime checks only after its open.
- Against a hostile host: a swap between the look and the open, by a host process or another call writing the same grant, is named as kept (Decision 6) and in both docs sentences. The guest that made the look cannot swap: it is inside its own host call, on its one thread (wasm32-wasip1 without threads). Holds.

## The 64 bytes at address 0

Safe. The plain `python.wasm` is linked stack first: its first global, the stack pointer, starts at 16,777,216, and its two data segments start at 16,777,216 and 26,067,024 (EXECUTED, `layout.log`), so bytes 0 to 63 are the far end of a 16 MiB C stack, live only for a guest within 64 bytes of overflowing it. Save and restore make their contents irrelevant either way. A path that overlaps the window opens the right file and the bytes come back (EXECUTED, `probe.log`: a path written at 0 opened `file`; bytes 0 to 63 set to 0..63 were the same after a look). A trap in the look is caught by `forward` itself and the `finally` restores; nothing runs guest code between save and restore. The snapshot was not read; it is made from the same link, so its stack pointer is the same (INFERRED).

A `host_alloc`'d buffer would be less safe: the reactor exports `host_alloc` (EXECUTED, `layout.log`), but calling it runs the guest's own code from inside its host call, re-entering an allocator that may be mid-operation, spending fuel and meeting the epoch, the case the door guards with its depth count (READ, `_call.py:1223-1268`); and the raw modules on the counted linker export none. Address 0 is the better choice.

## Acceptance criteria against evidence

1. Every row of Decision 10, red rows seen failing first — **designed to be met**. The FIFO rows wait today (the review's M1, EXECUTED there; the author's `opens.log`); the kept rows answer today as asserted (`EEXIST` under `O_CREAT|O_EXCL`, EXECUTED, `skipped.log`: 20; `ELOOP` without follow, READ, the author's `opens.log`). The 120 s daemon join is `_returns`'s fail-safe (READ, `test_v1_2_hostile_guest.py:781-793`), not a measurement, and the teardown's `O_RDWR | O_NONBLOCK` open gives a waiting open its other end, for reading or for writing, so a red run's worker returns (INFERRED). Finding 1 adds one unit row.
2. The unit file green on three systems, FIFO and socket rows skipped on Windows; the goal checks green, Windows by a regular file — **acceptable**. The unit suite counts a skip and does not judge it (READ, `plugin.py:500-507`); a goal check may skip only with a known, unmet need (READ, `plugin.py:510-523`, `needs.py`). A goal check whose body differs by platform has precedent (READ, `test_v1_2_hostile_guest.py:1225`, `:1326`, `:1531`). A new need such as the existing `read-only files` would make the Windows leg "blocked"; the regular-file body instead reads the look's common path through the artifact set, which is worth a leg.
3. No pass lost, no fuel or byte growth — **holds by construction**. wasmtime meters wasm instructions, not host calls; the look's trampoline instructions are paid by `FUEL_ALLOWANCE` and the fuel is set back in `forward`'s `finally` (READ, `_fs_table.py:234-265`). On today's wasmtime the look's error path is met only at the runner's own stop (finding 1), where `_fuel_used` answers `None` today too (READ, `_call.py:550-569`).
4. Structure — **met as designed**. `_path_open` is 78 lines today (EXECUTED, `ast`), about 72 after; `forward` 32, one keyword added; `_fs_paths.py` 578 lines, `_fs_table.py` 682, `_fs_memory.py` 281, `_call.py` 1,337 and untouched (EXECUTED, `wc -l`). No state, lock, private name or platform branch: the look reaches the engine through `forward`, behind `_wasmtime_ffi.py`.
5. The docs sentences — **as written, fit**: they replace `security-model.md:80` and `grants.md:119`, which are today's FIFO lines (READ), and name no specification or path.
6. The landing notes' count of `path_filestat_get` looks for `print('hello')` — **a count, not a time**; holds the rule.
7. The news file and `ci-status` — a build-time check.

## Findings, most severe first

1. **Low, fixed in the specification by me (`a8748c06`): the look's error path on today's wasmtime is the runner's own stop** (Decision 3's second bullet; `_call.py:745-765`, `:838-880`).
   - The defect: the bullet said a look that ends in a wasmtime error "records no stop, and the run goes on", and named a socket on a later wasmtime as its case. On today's wasmtime the case that reaches it is the epoch callback at the trampoline's entry, after the deadline, a `cancel` or a Ctrl-C: the callback has already recorded the stop, so the run does not go on.
   - What happens (EXECUTED, `epoch.log`): with the deadline passed as the look began, the look's forward raised the callback's error, a swallowed look answered 60 for a regular file, and the next call ended with "stopped by wasi_python" and `ended` "deadline". So the outcome is today's end, named as today; the guest sees `ENXIO` on its way out where today it sees the stopped errno, `EIO`. No harm, but the text promised otherwise and no row read it.
   - Written in: the bullet now says so, with the evidence, and Decision 10's third unit bullet adds a row: a look on a regular file whose trampoline meets the callback after the deadline answers, and the next call ends the run named "deadline".
2. **Low, fixed by me: the kept `EPERM` difference has a second form** (Decision 3's last paragraph; the news line).
   - With `O_DIRECTORY` and write rights on a read-only grant's FIFO, wasmtime answers 63 (EXECUTED, `skipped.log`), and the look, by the answers list, gives `ENOTDIR`. The text named only `ENXIO`. Now: "answers `ENXIO`, or `ENOTDIR` with `O_DIRECTORY`, where wasmtime answers `EPERM`", in Decision 3 and the news line. The row Decision 10 names for the difference should assert both.
3. **Low, fixed by me: `out` is not checked by the look, and that is a third kept difference** (Decision 3's first paragraph).
   - wasmtime writes `out` after its host open, so for `/dev/null` with a misaligned `out` it opens and then ends the run (READ, `p1.rs:2156-2210`, wiggle writes the result after the body). The look, as drafted, refuses a special file with `ENXIO` whatever `out` holds. That is the safe choice: an `out` check before the look would let a guest that passes a bad `out` reach the open that waits. It was unsaid, so a builder could have added the check "to leave it to wasmtime". The paragraph now says the look ignores `out`, why, and that a file or folder is forwarded and ends as today.
4. **Low, fixed by me: an undefined flag bit ends the run, not `EINVAL`** (Decision 3's first paragraph).
   - The parenthesis cited `p1.rs:1114-1119` for `EINVAL`. On wasmtime-py 50.0.1 an undefined bit in `oflags`, `fdflags` or a rights word ends the run with "Invalid flag value" (EXECUTED, `skipped.log`), as the mount branch's `_flags` ends it. The decision stands, since no host open is made; the evidence now reads as executed.
5. **Low, fixed by me: `FILESTAT` is taken** (Design, `_fs_memory.py`).
   - `_fs_memory.py:126` already defines `FILESTAT = "<QQB7xQQQQQ"`, the filestat's struct format, which `_fs_paths.py` imports. The Design's `FILESTAT = 64` would shadow it. Now `FILESTAT_SIZE = 64`, or `struct.calcsize(FILESTAT)`.
6. **Low, for the landing: the roadmap's reserved line says the opposite of Decision 5** (`context/roadmap.md:104`).
   - It says the runner "looks at the target without following it" and that a row "asserts the call ends with its deadline". The specification's Status says the refinement plainly for the owner, and Decision 10 says why the rows assert the exit. Fix text, for the builder's landing commit, which rewrites the line as landed: "143 (a `path_open` on a grant whose target is a FIFO, a socket or a device file is refused with `ENXIO`, or `ENOTDIR` under `O_DIRECTORY`, after a forwarded `path_filestat_get` on the open's own descriptor that follows links exactly as the open does; the rows assert the call returns with the refusal and `Session.close()` returns; …)".

## Structure

(checklist 4a) No concern, lifecycle flag, module-level mutable or lock, test seam, platform branch or private wasmtime-py name is added; `forward` gains one keyword, `_path_open` shrinks, the two new functions are short, and `_call.py` is untouched. No rubric row moves toward Weak; R2 (every channel to the host bounded) moves toward Strong. The Kind line's **not structural** holds.

## The owner's words

The owner approved "look at the target without following links". The specification follows links as the open does and says so in its Status ("Decision 5 refines the approved words … the pre-build review reads that first") and in Decision 5's reason, with the evidence: a look that never follows lets a guest's own link through to an open that waits. That is stated plainly enough for the owner to read and overrule; only the roadmap line still carries the old words (finding 6).

## Mounts

Out of scope, rightly. A provider answers `stat`, `list` and `read` with values, `Stat` kinds are only `"file"` or `"dir"` (READ, `mounts.py:7-13`; `_fs_table.py:643-644`), and the runner owns every descriptor: no host descriptor comes back from a provider. The mount branch never forwards (READ, `_fs_paths.py:114-169`). A mount's preopen is in the table, so an open on it takes the mount branch, never the look.

## Constitution checks

- §2, the sandbox promise: the look resolves inside wasmtime's sandbox, records no host path and gives the guest nothing its own `path_filestat_get` does not; it closes a hold past the deadline, `cancel` and `Session.close()`. Holds and is strengthened.
- §4.1, upstream patches: none. Decision 2 says why a non-blocking open would be a change to wasmtime and leaves it out. Holds.
- §5.6: its list (the guest's imports or exports, the artifact set, the build recipe) does not require this review; the specification asks for it because it changes what the guest sees for one call, as 140 did. Its answers are now named, kept differences included.
- §7 never-do list: nothing tripped. My probes counted answers, with a 5 s join only as a fail-safe; they ran under the worktree's ignored `build/`, touched no host but this machine, and copied nothing from prior art.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Findings 1 to 5 — written into the specification by the reviewer in `a8748c06`; the author may reword.
2. Finding 6 — for the landing commit.

## Verdict

Fit to build: the forwarded look is sound against a hostile guest and names its one host race, address 0 is a safe window, and the six Lows are written in (five in the specification, one for the landing).
