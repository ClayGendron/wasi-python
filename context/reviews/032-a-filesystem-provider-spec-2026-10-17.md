# Review of 032 — A filesystem provider, read-only mounts (the specification, before build; also a security review)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the constitution (§3, §4.3, §4.4, §4.9, §4.15, §5.6, §5.7), the threat model (`../research/2026-10-16-a-principal-engineers-direction.md` §2), the 0.1.0a3 security review, the 030 pre-build review (for its format), `decisions.md` (13, 16, 17, 24, 37, 41, 42), `questions-for-the-owner.md` (54 to 56), the specification, the research memo and its evidence (`imports.txt`, `dot_path.txt`, `shadow.py`), spec 030, and the runner (`_Defaults`, `Completed`, `run`, `_run_checked`, `_call_deferred`, `_home_folder`, `_instance`, `_drive`, `_Call`, `_shared`, `_epoch_answer`, `_linker`, `_poll_oneoff`, `_poll_plan`, `_door`, `_check_preopens`, `_Walked`, `_Private`, `_deferred_ctrl_c`). I read wasmtime 49's preview1 (`context/prior_art/wasmtime-v49/crates/wasi/src/p1.rs`), wasmtime-py 49's `Linker.get`, `WasiConfig.preopen_dir` and `_bindings.wasmtime_func_call`, the judge's import rule (`tests/harness/wasm.py:163-176`), the existing descriptor check (`tests/checks/test_v1_2_hostile_guest.py:396-445`), the `verify` job (`.github/workflows/release.yml:208-244`), and vfs's spec 169 §b3 to §b8 (read only). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/032-a-filesystem-provider.md` as drafted (committed in `a826af3`), against the runner on `a826af3`.
- **Ran (EXECUTED, darwin-arm64, `uv run python -I`, wasmtime-py 49, a copy of `build/artifacts/` in the scratchpad; `scripts/build.sh` and the judge not run).** Nothing in `src/`, `tests/`, `scripts/`, `recipes/` or the spec was edited. Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/032-review/`:
  - `grant_paths.py` → `grant_paths.txt`: today's runner, a read-only `Grant`, both binaries: what a grant answers for path forms a lexical normalizer treats differently.
  - `raw_answers.py` → `raw_answers.txt`: plain wasmtime-py, raw preview1 calls on a read-only grant's file, folder and preopen, and on a number reserved on an empty read-only placeholder (the memo's `path_open(".", O_DIRECTORY)`), which is what an unshadowed call on a provider descriptor reaches.
  - `iovecs.py` → `iovecs.txt`: raw `path_open` path forms, `fd_read` iovec handling, and out-of-bounds guest pointers on a read-only grant.
  - `reserve_limit.py` → `reserve_limit.txt`: how many numbers can be reserved before the host refuses, under soft `RLIMIT_NOFILE` 256, 1,024 and 4,096, and the errno then.
  - `forward_trap.py` → `forward_trap.txt`: a shadow that forwards through a trampoline while the epoch deadline is overdue, or with fuel spent.
  - `launchctl limit maxfiles` on this machine: `256 unlimited` (the soft limit a process launched by launchd starts with). This shell's `ulimit -n` is 1,048,576.

## What holds

- **The mechanism is sound, and it adds no import (§4.4).** READ: the memo executed shadow, trampoline and placeholder on both binaries. The guest's imports do not change. The spec keeps wasmtime's own WASI for everything it does not own, which keeps wasmtime's audited handling of grants, the zip and stdio. That is the right choice over defining preview1 ourselves.
- **A call without mounts can be truly unchanged.** READ: `_linker` is per engine and cached (`runner.py:1939-1958`). A second linker used only with mounts leaves today's object, its host functions and its fuel exactly as they are. Acceptance 10 asserts the linker's identity and a zero shadow count, and the ratchet holds fuel. That is the right check.
- **The safety net is real.** EXECUTED (`raw_answers.txt`): a reserved number is a read-only directory handle on the empty placeholder. Unshadowed calls on it answer `EBADF`, `ENOTDIR`, `ENOTSUP` or `ENOTSOCK`. Nothing on it reaches a host folder other than the placeholder. The placeholder lies in the call's `0700` scratch folder, which no grant may be at or above (`_shared_folders`).
- **The `sock_*` calls and the prestat pair need no shadow.** EXECUTED (`raw_answers.txt`): `sock_accept`, `sock_recv`, `sock_send` and `sock_shutdown` answer 57 (`ENOTSOCK`) on a grant file, a grant folder, a preopen and a reserved number alike. `fd_prestat_get` and `fd_prestat_dir_name` answer 8 and 54 on a reserved number, as on a grant's opened file or folder. `poll_oneoff` is the runner's own and answers by number only (`_poll_plan`), so a provider descriptor is treated as a grant's descriptor is.
- **Values, not exceptions (question 54), is the right protocol.** READ: vfs's table (`169…/spec.md` §b7) uses 18 errnos, all in the spec's `Errno` set. A host `OSError`'s `errno` is host numbering (Windows differs from POSIX), so accepting `OSError` would bring a host-specific mapping into the runner (§4.3). An exception meaning "a bug" is clean.
- **Faults never escape, by construction.** READ: Decision 4 follows `_door` and `_shared`. `BaseException` is recorded as the stop and raised from `run`. Nothing goes through wasmtime-py's exception slot.
- **Time.** READ: a sync provider cannot be interrupted, and the spec says so. Cancel and the deadline are checked before every provider call, and `_shared` checks cancel after. A deferred Ctrl-C on the main thread also waits for a blocked provider, as it waits for a blocked door host today (`_deferred_ctrl_c`). The README should say that too.
- **Threads (spec 011).** READ: the shadows are `_shared`'s form, the mount table and the record are per call, and the trampoline is per call. Nothing new is shared between calls, once finding 1's per-call rule is written down.
- **Fuel stays deterministic.** INFERRED from the memo's finding 3: a forward costs the trampoline's few instructions, and a provider-served call costs none. A mounted run's fuel depends only on how many calls it forwards. It is not comparable with an unmounted run, and no check compares them.
- **The limit stops the run and names it (decision 42).** READ: with an epoch deadline of 0, the next function entry traps. `_drive` reads `call.ended` when nothing is recorded in `call.stopped` (`runner.py:1749-1760`), so `"out of file calls"` wins over the raw `INTERRUPT` without a callback. Under `cancel=`, the new `_epoch_answer` rule keeps it.
- **It is not build-class.** READ: it touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or workflow file. But see finding 6 on what that costs.

## Acceptance criteria against evidence

1. `test_a_mount_serves_reads`: well formed; counts only.
2. `test_a_mount_answers_as_a_grant_does`: two rows cannot pass as written (finding 3: "a path over 4,096 bytes" is `ENOENT` on a macOS grant). Sizes must be file sizes (a folder's size is host-dependent).
3. `test_raw_calls_answer_as_a_grant_does`: compares errnos only, and several rows contradict Decisions 5 and 7 (finding 3). It also runs on one system only (finding 6).
4. `test_a_mount_at_the_root`: sound. The pinned start-up count will change with every build-class change to the zip or CPython (finding 8).
5. `test_the_file_call_limit_stops_the_run`: sound.
6. `test_a_mount_keeps_its_deadline_and_cancel`: sound; the ticker seam exists (`tests/unit/test_runner_async.py:24`, spec 017's check). A forward that meets the overdue deadline is not covered (finding 1).
7. `test_a_provider_fault_never_escapes`: sound in content; not run by `verify` (finding 6).
8. `test_guest_arguments_never_reach_the_provider`: its rows conflict with wasmtime's answers (finding 3). `test_mount_descriptors_are_bounded` fails under a 1,024 or 256 descriptor limit (finding 2).
9. to 11.: sound.
12. and 13.: right.

"Seen failing first … by a stand-in" is weak for the guards (finding 8).

## Findings, most severe first

1. **A forward is guest-side wasm, so it can trap inside a shadow, and the spec does not say what the shadow does then.** High. This is the boundary's error path, and it meets spec 030's fix.
   - EXECUTED (`forward_trap.txt`): a shadow that forwards through a trampoline gets `Trap(INTERRUPT)` when the epoch deadline is overdue, and `Trap(OUT_OF_FUEL)` when fuel is spent. The trampoline's function entry is an epoch check, and its instructions burn fuel.
   - EXECUTED (`iovecs.txt`): wasmtime answers an out-of-bounds guest pointer (path, `iovec` array, `iovec` buffer, result pointer) with an error ("Pointer out of bounds"), not with `EFAULT`. So any forwarded grant call with a bad pointer raises inside the shadow.
   - READ: under `cancel=`, the epoch callback runs at the trampoline's entry, sets `call.ended` and returns its error. If the shadow lets `_shared` record that error, the run is named by the raw error. That is the defect spec 030 fixes for `host_alloc`, reborn on a new path. If the shadow swallows every error and returns an errno, a bad pointer on a grant no longer ends the run, which changes today's outcome for the same guest.
   - READ: the forward uses `_ffi.wasmtime_func_call`, which hands back a trap or error object. The spec does not say it is freed, or turned into which outcome. It also does not say that the cached argument arrays and the trampoline's `wasmtime_func_t` are per call. A func of one store used with another store's context makes wasmtime abort the process (INFERRED from wasmtime's store-ownership checks). A shared argument array races between threads.
   - Fix: add to Decision 1. "A trap or error from a forward or a reservation is raised to the shared function, exactly as `_door` re-raises `host_alloc`'s (spec 011), so spec 030's rule names a cancel or a deadline and anything else is recorded as today. The trap or error object is freed. The forward runs on `caller._context()`. Its function and argument arrays live on `_Call`, never on the engine." Say that a mounted run that runs out of fuel inside a forward reports `"out of fuel"` with `fuel_used` `None`, as a door call's `host_alloc` does today, or make `OUT_OF_FUEL` sticky (return and let the guest trap at its next instruction, which keeps `fuel_used` exact). Add a check: a mounted guest with a tiny fuel cap ends `"out of fuel"`; a cancel during a run of forwarded calls ends `"cancelled"` (030's ticker pattern); a raw bad pointer on a grant descriptor in a mounted call ends as it ends without mounts.

2. **Each provider descriptor costs one host descriptor, and hosts run out before 1,024.** High. It breaks acceptance 8 on common hosts, and the failure path is unspecified.
   - EXECUTED (`reserve_limit.txt`): with soft `RLIMIT_NOFILE` 256, 249 numbers were reserved, then wasmtime answered 29 (`EIO`). With 1,024: 1,017, then 29. With 4,096: all 1,100. The 0.1.0a3 security review saw the same on grants (1,011 files at 1,024, then 29).
   - EXECUTED: `launchctl limit maxfiles` is `256` here, the soft limit of a process launchd starts. Many Linux systems default to 1,024.
   - So `test_mount_descriptors_are_bounded` (1,025 files, `EMFILE` on the last) fails on such hosts: the guest meets `EIO` near 250 or 1,017, never `EMFILE`. Concurrent mounted calls share the embedder's one descriptor table, so a guest can starve the embedder's own sockets and files (threat model asset 5). A grant has the same exposure today; the mount adds it at no benefit, since the handle only buys a number.
   - The spec does not say whether the reservation comes before or after the provider call. If after, a failed reservation wastes a counted `read` and its staged bytes.
   - Fix: reserve first. A reservation that fails answers `EMFILE` (33) with no provider call and no count. Keep `MAX_MOUNT_FILES` as the runner's bound, and say in the README that the host's descriptor limit may be lower. Rewrite the check like `test_a_guest_that_uses_up_host_descriptors_cannot_make_run_raise`: in a child with the limit raised to at least 2,048 for the 1,025 row, and a second child at 256 where the guest gets `EMFILE`, `run` returns exit 0, the provider's `read` count equals the successful opens, and nothing is left behind. An alternative worth a sentence in the spec: number provider descriptors from a high base (for example `2**30`) that wasmtime's `unused()` never reaches (`p1.rs:434-466`). That costs no host handle, and a forward of such a number answers `EBADF`. The trade is the lowest-number rule POSIX programs may assume.

3. **The parity claim ("every answer is a read-only grant's") is contradicted by the spec's own rules, and a grant's answers depend on the host.** Medium-high. The builder would face two authorities that disagree.
   - EXECUTED (`grant_paths.txt`, both binaries, and `iovecs.txt`, raw):

     | input on a read-only grant | wasmtime's answer | the spec's rule gives |
     |---|---|---|
     | `missing/../b.txt` | 44 `ENOENT` | success (`..` resolved by text) |
     | `a.txt/../b.txt` | 54 `ENOTDIR` | success |
     | `a.txt/.` | 54 `ENOTDIR` | the file (`.` dropped) |
     | `""` (empty path, raw) | 44 `ENOENT` | the mount's own folder (empty parts dropped) |
     | `/f.txt` given to a descriptor (raw) | 63 `EPERM` | unstated; "empty parts dropped" makes it relative |
     | a path of 4,097 or 5,000 bytes (parts of 200) | 44 `ENOENT` (macOS) | 37 `ENAMETOOLONG` |
     | a pointer past memory | an error that ends the run | 21 `EFAULT` |
     | 1,025 `iovec`s | success, 1 byte read | 28 `EINVAL` |
     | `readv` of two 3-byte `iovec`s, 6-byte file | 3 bytes (first non-empty only, `p1.rs:203-219`) | unstated |
     | `fd_advise`, `fd_fdstat_set_flags` on a folder | 8 `EBADF` (`raw_answers.txt`) | success ("succeed on a provider descriptor") |
     | `fd_fdstat_set_flags(SYNC)` on a file | 28 `EINVAL` | success |
     | `/data/A.TXT` when `a.txt` exists | the file (macOS is case-insensitive) | `ENOENT` from a case-sensitive provider |

   - Also EXECUTED: a NUL in a raw path is 28, bytes that are not UTF-8 are 25 (`EILSEQ`), and `readlink` of a file is 28. Decision 6's `readlink` row matches.
   - None of these is a hole. Lexical `..` cannot leave the mount, because the climb check runs first. It even leaks less: a grant tells a guest whether `x` exists through `x/../f`. Refusing long paths and bad pointers early is safer. But "the two errnos are equal in every case" cannot pass, and Decision 6 calls the parity checks "the authority".
   - Fix: give Decision 6 a short table of deliberate differences, each with its reason: `..` resolved by text, a 4,096-byte bound, `EFAULT` for a bad pointer, a 1,024 `iovec` bound, a case-sensitive provider. Keep everything else at parity. Decide the four unstated rows: an empty path is `ENOENT`, a leading `/` is `EPERM`, `.` after a file is `ENOTDIR`, and a read fills only the first non-empty `iovec`, as wasmtime does. Correct the `fd_advise` and `fd_fdstat_set_flags` sentence to "as a grant's file or folder answers". Take wasmtime on Linux as the reference. A row whose grant answer differs by host is left out or asserted per host. Make acceptance 3 compare the whole result, not only the errno: the bytes each call writes (`nread`, filetype, size, offsets, the `fd_readdir` buffer), with `dev`, `ino`, times and descriptor numbers masked.

4. **Not every descriptor-taking import is shadowed, and `fd_renumber`'s shadow is not defined.** Medium. Nothing is reachable today; the risk is the next binary.
   - READ: preview1 has three descriptor calls the binaries do not import: `fd_renumber`, `fd_allocate` and `fd_fdstat_set_rights` (`imports.txt`). The spec shadows only the first. The judge's import rule admits any preview1 name (`tests/harness/wasm.py:163-176`), so a rebuild that starts importing `fd_allocate` passes the judge silently.
   - EXECUTED (`raw_answers.txt`): `fd_allocate` on a reserved number is 8; on a grant file it is 58. Parity breaks without a shadow.
   - EXECUTED: `fd_renumber(grant file → reserved number)` succeeds. wasmtime silently closes the reserved handle and puts the grant's file at that number. A table that still held the number would serve provider bytes for a grant's file. The spec shadows the call "so a later binary cannot free a provider number", but never says what the shadow answers.
   - READ: the guest can also close a mount's own preopen. wasmtime then reuses that number for the next open (`p1.rs:456-466`). Decision 1 says the table drops a number at `fd_close`, but names only provider files and folders.
   - Fix: shadow all 29 descriptor calls (the 26, plus `fd_renumber`, `fd_allocate` and `fd_fdstat_set_rights`; it costs nothing without mounts). Define `fd_renumber`: when either number is in the table, answer `ENOTSUP` (58) and change nothing; otherwise forward. Say that `fd_close` on a mount's preopen drops it from the table too. Add a unit check that reads each binary's preview1 imports. Every import that takes a descriptor must be shadowed or be on a reviewed forward-safe list (`fd_prestat_get`, `fd_prestat_dir_name`, `sock_*`, `poll_oneoff`), so a new import fails the judge.

5. **Spec 030's invariant is broken by the new end, and nothing says so.** Medium-low.
   - READ: 030's Decision 3 writes into the code "`call.ended` is set only by the epoch callback, and only on a path that returns an error". Spec 032's shadow sets `call.ended = "out of file calls"` itself. The behaviour is still right: 030's entry guard returns `stopped` for every later host call, and the deadline of 0 stops the guest. But the comment that stops someone widening the guard would now be false.
   - Fix: 032 amends that comment, and says why the branch stays correct. `ended` is set only where the guest is also stopped by the runner's own act: the callback's error, or an epoch deadline of 0 set in the same step.

6. **"Its checks run on Windows, Linux and macOS" is not true for half of them.** Medium.
   - READ: `verify` runs `test_v1_1_artifact_set.py`, `test_v1_2_portable_and_sealed.py`, `test_v1_3_data_stack.py`, `test_v1_4_embedding.py`, `test_runner_sweep.py`, `test_runner_grants.py` and `test_cli.py` (`release.yml:239-244`). It does not run `test_v1_2_hostile_guest.py` (acceptance 7, and 8's descriptor check) or the new `test_runner_mounts.py` (acceptance 3, 8, 9, 10). So the raw parity table, the part that depends most on the host, never runs on Windows or Linux.
   - Fix: put the raw parity cases in `tests/unit/test_runner_grants.py`, which `verify` already runs. They are grant parity, so they belong there. That keeps the spec out of build-class. Correct the Kind line to name what does not run on three systems, or accept build-class and edit the workflow.

7. **The staging bound is unbounded when `memory_bytes=None`, though the guest is not.** Medium-low. This is question 55.
   - READ: Decision 8 says staging is bounded by `memory_bytes` "and unbounded when it is `None`", because "the guest could hold as much in its own memory". With `None`, the guest is still held to wasm32's 4 GiB. Staging is then held by nothing, across up to 1,024 files and their listings.
   - READ: the bound is checked after the provider made its answer (`memoryview(...).nbytes`). So it bounds what the runner keeps, not the provider's peak. A listing's 24 bytes per entry undercount the Python objects behind it several times over (INFERRED).
   - Fix: bound staging by `memory_bytes`, or 4 GiB when it is `None`. Say in the README that the bound is on what the runner keeps, and that a provider should refuse a large file before it reads it (vfs judges on `size_bytes` first, `169…/spec.md` §b8).

8. **"Seen failing first by a stand-in" proves little for the guards, and one pin will churn.** Low-medium.
   - READ: on today's runner every new check fails at `import Mount`. That shows nothing about acceptance 3, 7 or 8, which exist to catch a missing guard.
   - Fix: for 3, 7 and 8, the landing notes show each check failing against a build with one guard removed (no pointer check, no name check, no fault catch, no climb check), then passing. Acceptance 4's exact start-up count should be recorded as a metric the ratchet follows, or asserted as a bound. Then a change to the zip or to CPython does not edit a security check.

9. **Small gaps in what counts as a bad answer, and two unstated choices.** Low.
   - A listing name that cannot be encoded as UTF-8 (a lone surrogate) or is over 255 bytes is not named a bad answer. Encoding it would raise inside the runner. `bool` passes as `int` for `size` and `mtime_ns`. Iterating a listing, and reading a `read` answer's buffer, run provider code, so they must sit inside the fault boundary.
   - `dev` and `ino` are "a 64-bit hash". Python's `hash()` of a `str` is randomized per process, which breaks "a run repeats exactly". Name the keyed hash `_wasi_ino` already uses (`_siphash13`).
   - `_shared`'s `refused` and `stopped` codes for the file shadows are not named. Suggest `EBADF` (8) and `EIO` (29).
   - The scratch folder is made after the `preopen_dir` loop today (`runner.py:1640-1652`). The placeholder must exist first, so the builder reorders `_instance`. Say so.

10. **vfs's adapter is not quite `Errno(WASI_ERRNO[kind])`.** Low.
    - READ: vfs maps `wrong_kind` to 54 (`ENOTDIR`) (`169…/spec.md:437-447`). Its own shim picks 31 (`EISDIR`) when the target itself is a folder (§b4). The runner makes a folder descriptor only on `EISDIR` from `read`. So a one-line adapter would make `os.open(folder, O_RDONLY)` fail with `ENOTDIR`.
    - Fix: state `read`'s contract in Decision 3. `read` answers `EISDIR` when the path itself is a folder, and `ENOTDIR` when a parent is a file. Drop the one-line-adapter claim, or add that rule to it.

## Is it one builder's work?

Yes, but only with a build order. It is about 700 to 900 lines of boundary code (the memo's estimate), 27 to 29 shadows and a raw parity harness. Suggested order, each step green before the next:

1. The mount linker with every shadow forwarding (no provider), plus finding 1's trap rule. The judge, run with a pass-through mount, gives today's answers.
2. The table, the placeholder and the reservation (finding 2).
3. `path_open`, `fd_read`, `fd_seek`, `fd_close`, `fd_readdir` and the filestat calls on a provider.
4. The rest of the parity table, the limits, the record, and the docs.

Build the raw parity harness first, table-driven: one WAT module that re-exports each preview1 call with its raw signature, as `raw_answers.py` does. A row is then data, not a new guest.

## On questions 54 to 56

- **54 (answers, not exceptions):** agree. See "What holds".
- **55 (staging bounded by `memory_bytes`):** agree, except when it is `None` (finding 7).
- **56 (names):** agree. `"out of file calls"` reads well beside `"out of fuel"`.

## Constitution checks

- **§4.4, two channels:** holds. No import is added. EXECUTED by the memo on both binaries; READ here.
- **§4.3, one target, no host-specific branch:** at risk only in the parity checks, which compare against host-dependent grant answers (finding 3). The runner's own answers are host-independent.
- **§4.5, embedder-neutral:** holds. No vfs name in the API; the `Errno` set is preview1's.
- **§4.9, tests count:** holds. Every criterion counts calls, bytes or errnos. Acceptance 6 waits by ticker count, as spec 030 does.
- **§4.10, claims carry evidence:** the memo's claims are labelled. The spec's parity claim outruns them (finding 3).
- **§4.15, safe by default:** holds for "no channel without an argument": no mount, no provider call. Every limit has a default, except staging when `memory_bytes=None` (finding 7). The descriptor bound is real only on hosts with a high limit (finding 2).
- **§5.6, review before build:** this review. A build review that is also a security review is already acceptance 13.
- **§5.7, one landing lane:** not build-class, if finding 6 is fixed by placement rather than by a workflow edit.

## Disposition (filled in by the author, then confirmed by the reviewer)

By the author, 2026-10-17. Each finding is fixed in the specification; the decision or criterion that carries it is named.

1. **Fixed (Decision 1, acceptance 6 and 12).** A trap or error from a forward is taken into wasmtime-py's own `Trap` or `WasmtimeError` (`_from_ptr`, which owns and frees it) and raised to the shared function, as `_door` raises `host_alloc`'s. So with spec 030 a cancel or a deadline under `cancel=` is named from `call.ended`, and anything else (a bad pointer on a grant's descriptor) is recorded and named as without mounts. The forward runs on `caller._context()`, and its function handles and argument arrays live on `_Call`. For fuel I took a third way rather than naming or a sticky trap: **a forward is fuel-neutral.** The shadow reads the fuel, adds the trampoline's allowance, forwards, and sets it back. So `OUT_OF_FUEL` cannot occur inside a forward, `fuel_used` counts only the guest's instructions (spec 008), and a mounted run's fuel equals the same run with an empty grant in the mount's place. Acceptance 12 pins that equality, the out-of-fuel ending and the bad-pointer ending (INFERRED that `set_fuel` is allowed during a host call; the check is where it is proved, in build step 1). Acceptance 6 adds a cancel during a run of forwarded calls.
2. **Fixed by the alternative (Decision 1, Decision 8, acceptance 1 and 8).** Provider numbers come from `2**30` up and live only in the call's table. wasmtime never reaches that range (`p1.rs:434-466`), and each of its own numbers costs a host handle, so it cannot. No reservation and no host handle is spent per provider file; a forward of such a number answers `EBADF`. `MAX_MOUNT_FILES` (1,024) is checked before the provider call, so `EMFILE` makes no call and counts none, and it holds at any host descriptor limit: `test_mount_descriptors_are_bounded` runs in a child at a soft limit of 256. The trade, the lowest-number rule, is stated; acceptance 1 opens, reads, scans and selects on such numbers.
3. **Fixed (Decisions 5 and 6, acceptance 2 and 3).** Decision 6 now has a table of deliberate differences with reasons (`..` by text, the 4,096-byte bound, `EFAULT`, the `iovec` bound, case, `EBADF` for forward-safe calls on provider numbers, high numbers). The four unstated rows are decided: an empty path is `ENOENT`, a leading `/` is `EPERM`, a trailing `/` or `/.` on a file is `ENOTDIR`, and a vectored read fills only the first non-empty `iovec`. Non-UTF-8 is `EILSEQ` and NUL is `EINVAL`, as wasmtime answers. `fd_advise` and `fd_fdstat_set_flags` answer as a grant's file or folder. The reference is wasmtime on Linux; acceptance 3 compares whole results with `dev`, `ino`, times and numbers masked, and a row that differs by system is asserted per system. The 4,096-byte row left acceptance 2's parity list.
4. **Fixed (Decision 1, acceptance 13).** All 29 non-forward-safe descriptor calls are shadowed. `fd_renumber` answers `ENOTSUP` and changes nothing when either number is in the table or at or above `2**30`; otherwise it is forwarded. `fd_close` on a mount's preopen is forwarded and drops it from the table. A unit check reads each binary's imports: every descriptor import is shadowed or on the reviewed forward-safe list (`fd_prestat_get`, `fd_prestat_dir_name`, `sock_*`, `poll_oneoff`).
5. **Fixed (Decision 9).** 032 replaces 030's comment, when it lands, with: `call.ended` is set only where the runner also stops the guest by its own act in the same step (the epoch callback on an error path, or the file-call limit's shadow, which sets the deadline to 0 before it returns). The branch stays correct because 030's entry guard keeps every later host function, forwards included, from running once `ended` is set, and the limit's shadow raises nothing. Acceptance 5 under `cancel=` shows it.
6. **Fixed by placement (Kind line, Design).** The raw parity table moves into `tests/unit/test_runner_grants.py`, which `verify` already runs, so it runs on all three systems and the spec stays out of build-class. The Kind line now says which checks run on three systems (v1.4 and the raw parity) and which on the judge's machine only (the hostile and guard checks, which test host-independent runner code).
7. **Fixed (Decision 8; question 55 updated).** Staging is bounded by `memory_bytes`, or 4 GiB when it is `None`. A listing is kept as its encoded preview1 entries, so the count is what the runner holds. The README says the bound is on what the runner keeps and that a provider should refuse a large file before reading it.
8. **Fixed (Acceptance criteria preamble, acceptance 4).** For 3, 7, 8 and 13, "seen failing first" means against the built runner with one named guard removed at a time, each check failing on its own guard. Acceptance 4's start-up count is asserted as a bound at twice the measured count, with the counts in the landing notes. (The judge's `metric` fixture takes only `fuel` and `bytes`, so a ratchet metric would need a judge change; a bound needs none.)
9. **Fixed (Decisions 1, 4 and 6).** Bad answers now include a name that cannot be encoded as UTF-8 or is over 255 bytes, and a `bool` for `size` or `mtime_ns`; iterating a listing and reading a buffer sit inside the fault boundary (acceptance 7 covers both). `dev` and `ino` are `_siphash13` with zero keys, as `_wasi_ino`, never `hash()`. The file shadows' codes are `EBADF` (refused) and `EIO` (stopped). `_instance` makes the scratch folder and placeholder before its `preopen_dir` loop.
10. **Fixed (Decision 3).** `read`'s contract: `EISDIR` when the path itself is a folder, `ENOTDIR` when a parent is a file. The one-line-adapter claim is replaced: a vfs adapter maps through its table with one rule of its own, `wrong_kind` on the target is `EISDIR`, as its shim already decides.

**The build order** is in the Design section ("Build order"): the review's four steps, with step 2 now the table and provider numbers instead of a reservation, and the table-driven raw parity harness built first. The Status line records this review and that no further pre-build review is needed once 1 to 4 are fixed, as the verdict says.

## Verdict

Not ready to build as written. The design is right, and it keeps the wall whole. Findings 1 to 4 change what the builder must do at the boundary. Fix them in the spec (traps in a forward, the reservation's failure, the list of parity exceptions, and every descriptor call shadowed), answer 5 to 10, and it is ready for build with no further pre-build review. The fixes are text and checks, not a new design.

## One line

A sound, import-free design whose spec leaves open three boundary paths: a trap inside a forward, a host out of descriptors, and the next binary's new imports. It also claims a grant's exact answers where its own rules differ. Write those down, and it can be built.

## Confirmation (2026-10-17)

By the reviewer. I read the revised specification and the Disposition above. I checked each answer against its finding. I also prototyped the two new designs: fuel-neutral forwards, and provider numbers from `2**30`. New scripts and outputs are in the same scratch folder (`fuel_neutral.py` → `fuel_neutral.txt`, `fuel_repeat.py` → `fuel_repeat.txt`, `high_numbers.py` → `high_numbers.txt`). They ran under `uv run python -I` on darwin-arm64, with wasmtime-py 49 and the artifact copy. Nothing in `src/`, `tests/`, `scripts/`, `recipes/` or the spec was edited.

### The ten dispositions

1. **Confirmed (EXECUTED).** `fuel_neutral.py` does what the revised Decision 1 says. The shadow forwards through a trampoline with `_ffi.wasmtime_func_call` on `caller._context()`. Its argument arrays and function handle are per store. A trap comes back through `Trap._from_ptr`, an error through `WasmtimeError._from_ptr`, and the shadow raises it.
   - **`set_fuel` during a host call works.** Reading the fuel, adding the allowance, forwarding and setting it back, all on the caller's context, raises nothing. The guest sees the restored value after the call returns. The spec's INFERRED is now EXECUTED for wasmtime 49.
   - **Neutral forwards cost exactly what wasmtime's own WASI costs.** 1,000 forwarded `fd_fdstat_get`s: today 17,005 fuel, plain forwards 21,005 (4 per forward), neutral forwards 17,005.
   - **Same endings at every cap.** With a cap near the end, today and neutral end the same way with the same fuel used, at every cap tried (17,004 down to 16,993). Every cap from 1 to 39 also matches. Without neutrality, `OUT_OF_FUEL` fired inside the forward at 16,997 and 16,993. With it, never.
   - **A bad pointer ends the same way.** A forwarded bad pointer gives the same error with or without the shadow (`Pointer out of bounds`), at the same fuel used (8).
   - Notes for the builder (finding N3).
2. **Confirmed, with finding N1.** High numbers remove the host handle per file and the reservation module. wasmtime's table never holds such a number: the `fd_renumber` rule refuses any number at or above `2**30`, and `unused()` grows only from wasmtime's own keys. `MAX_MOUNT_FILES` is checked before the provider call. EXECUTED (`high_numbers.txt`, both binaries): the guest's CPython passes `2**30` through to the host for `os.fstat`, `os.read`, `os.get_blocking` and `open(fd)`, all answering `EBADF` while the number is not open. `select.poll` and `selectors.DefaultSelector` (a `PollSelector`) accept it. But `select.select` refuses it in the guest.
3. **Confirmed (READ).** Decision 6's table of differences matches every row I executed. So do the four decided rows (empty path, leading `/`, `/.` on a file, first non-empty `iovec`). Acceptance 3 now compares whole results with the right fields masked.
4. **Confirmed (READ).** 29 shadows, the forward-safe list, `fd_renumber`'s `ENOTSUP` rule (which now also covers the high range), and `fd_close` on a mount's preopen. Acceptance 13 has the import check.
5. **Confirmed (READ).** Decision 9's new wording is true. `ended` is set only together with a stop the runner makes itself. After that, 030's entry guard keeps every shadow, and so every forward, from running. A callback error raised inside a forward meets 030's branch with `ended` set, as intended.
6. **Confirmed (READ).** The raw parity table now lives in `tests/unit/test_runner_grants.py`, which `verify` runs. The Kind line says honestly what runs on one machine only. The spec is still not build-class.
7. **Confirmed (READ).**
8. **Confirmed (READ).** Removing one guard at a time is the right way to show a check failing first. A bound on the start-up count needs no judge change.
9. **Confirmed (READ).**
10. **Confirmed (READ).**

### New findings

N1. **`select.select` refuses provider numbers, so acceptance 1 cannot pass as written.** Medium-low. EXECUTED (`high_numbers.txt`, both binaries): `select.select([2**30], [], [], 0)` and `select.select([1024], [], [], 0)` raise `ValueError: filedescriptor out of range in select()`. 1,023 is accepted. CPython checks against `FD_SETSIZE` (1,024) inside the guest, before any call reaches the runner. Decision 1's INFERRED ("its `select` and `poll` go through `poll_oneoff`") is true for `poll`, not for `select`. `select.poll` and `selectors.DefaultSelector` (here a `PollSelector`, which `asyncio` uses) work with `2**30`. Fix: acceptance 1 uses `select.poll` and `selectors.DefaultSelector`, not `select.select`. Decision 6's table and the README gain one row: `select.select` on a mount's file raises `ValueError`; use `selectors` or `select.poll`. Do not move the base below 1,024. Any number wasmtime can reach would bring back the collision the high range avoids.

N2. **Acceptance 12's "exactly the fuel" through `run()` will flake, and cannot see what it guards.** Medium-low. EXECUTED (`fuel_repeat.txt`): four identical `run()` calls (a print and a read of a grant, fuel capped at 10**11) spent between 82,377,594 and 82,388,007 on the snapshot (a spread of 10,413), and 284,367 apart on the plain binary. The real clock and entropy move the count. `test_fuel_does_not_depend_on_the_module_cache` allows 1,000,000 for this reason. The leak acceptance 12 must catch is 4 fuel per forward, a few thousand per run at most. That is below the noise. Fix: assert the exact equality where it is deterministic. Use the WAT module in `test_runner_mounts.py`: a guest calling a WASI function N times spends exactly the same fuel on the mount linker as on today's linker. It must also end the same way at a range of small caps (`fuel_neutral.py` is the pattern; equal to the unit, EXECUTED). Keep the v1.4 part to what is exact through `run()`: with a cap too small to finish, a mounted run ends `"out of fuel"` with `fuel_used` equal to the cap, as the grant run does.

N3. **Notes for the builder, no change to the spec needed.** Low.
   - Never forward through `Func.__call__`. Its `enter_wasm` calls `maybe_raise_last_exn`, which reads wasmtime-py's process-wide exception slot. It could raise another thread's exception (spec 011). READ: `wasmtime/_func.py:231-250`. Call `_ffi.wasmtime_func_call` and wrap the result with `_from_ptr`, as the spec says.
   - Restore the fuel in a `finally`, before raising. The bad-pointer row then keeps today's fuel.
   - Read and set fuel only on a metered call. `wasmtime_context_get_fuel` returns an error on an engine without fuel.
   - The allowance only needs to cover the trampoline's few instructions. Any larger constant is harmless, because the fuel is set back.

### Result

**Confirmed for build,** on two conditions, both text changes to the specification. No further pre-build review is needed:
1. N1: acceptance 1 tests `select.poll` and `selectors`. Decision 6 and the README name `select.select`'s refusal.
2. N2: acceptance 12's exact fuel equality moves to the WAT-level unit check. Its v1.4 part asserts only the `"out of fuel"` ending and `fuel_used` equal to the cap.

One line: the revision fixes all ten findings, and both new designs hold when run. Fix acceptance 1's `select` and acceptance 12's exact fuel through `run()`, and 032 can be built.

### The author's note on the conditions (2026-10-17)

All written into the specification; the Status line now reads "confirmed for build with conditions, written in".

- **N1:** Decision 1's high-range bullet now states what the confirmation ran (`os.fstat`, `os.read`, `open(fd)`, `select.poll` and `selectors` accept `2**30`; `select.select` refuses any number from 1,024) and keeps the base at `2**30`, with the reason. Decision 6's table gains a `select.select` row; Decision 12 (the README) says to use `selectors` or `select.poll`. Acceptance 1 tests `os.read`, `select.poll` and `selectors.DefaultSelector`, and asserts that `select.select` raises `ValueError`.
- **N2:** acceptance 12 is in two parts. The exact fuel equality, the endings at a range of small caps and the bad-pointer ending are in `tests/unit/test_runner_mounts.py`, through the WAT module. Through `run()` it asserts only the `"out of fuel"` ending with `fuel_used` equal to the cap, as with a grant. The Design table says so.
- **N3:** in Decision 1. The forward bullet says a forward never goes through `Func.__call__`, and why. The fuel-neutral bullet cites the confirmation's evidence (now EXECUTED, not INFERRED) and has the three rules: fuel read and set only on a metered call, set back in a `finally` before any trap or error is raised, and an allowance that only needs to cover the trampoline.
