# A cap on files open at once

- **Status:** research, 2026-10-18. It commits the project to nothing. It feeds spec 068 (`../specifications/068-a-cap-on-open-files.md`).
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), the author of spec 068's draft. It wrote none of the code it reads. Box: 2 hours.
- **The question,** from the owner's answer to question 92 (`../decisions.md`, "The owner's answers of 2026-10-18, evening"): a per-sandbox limit on files open at once, set by the embedder like the other limits, default 1,024, `EMFILE` past it, for `run` and sessions alike. Where does a guest make a host descriptor? How can the runner count them reliably on wasmtime 49.0.0? What does counting cost? How does it meet `max_file_calls`, mounts and sessions?

## Labels

EXECUTED means run here, on macOS arm64 (darwin), CPython 3.14.2, wasmtime-py 49.0.0 (which embeds wasmtime 49.0.0), from the worktree `../wasi_python-068` at main `434a811`, against the frozen artifact set `build/sets/s-4eb5418a2b1bb553-c353b1d9` of the main tree. The scripts and their output sit beside this memo, in `2026-10-18-a-cap-on-open-files/`; a copy is in the main tree under `build/reviews-evidence/068-spec/`. READ means read from a file, cited by path; `p1.rs` is `crates/wasi/src/p1.rs` of the wasmtime clone `context/prior_art/wasmtime-v49` (tag v49.0.3; why that is enough is said in §2). INFERRED means the researcher's reasoning. Times are benchmark facts of this one machine, never a check's assertion.

Some probes need a prototype of the counting applied to `src/` (`prototype068.diff`, beside the scripts; applied with `git apply`, measured, and reversed with `git apply -R`; nothing of it is committed). In the prototype the cap is a private module global, `runner._PROTO_OPEN_FILES` (default 1,024), not yet a keyword, so the public API and every judge file stay as they are.

## 1. The fact behind the decision (EXECUTED, by spec 055's pre-build review)

The review's probe `pb_fd_exhaust` (`build/reviews-evidence/055-review/probes/` in the main tree) had one guest call open files in a grant until refused. Under a soft limit of 1,024 the guest opened 1,014; under macOS's default it opened 122,870. Either way a `host=` function in that same call then failed `open()` with `EMFILE`. The 0.1.0a2 security review's F11 had seen the same from another side: while one guest held the descriptors, a second `run` on another thread raised `OSError: [Errno 24]` on the stdlib zip before its guest ran. The README's *Not protected* says so today, and that "wasmtime-py offers no lower limit".

## 2. Where a guest makes a host descriptor (READ, EXECUTED)

- **`path_open` is the only preview1 call that makes one the guest keeps** (READ, `p1.rs`). `path_open` (line 2156) opens through `filesystem().open_at` and pushes a `Descriptor::File` or `Descriptor::Directory` into the adapter's table, which holds one host file or folder handle (a cap-std `File` or `Dir`).
  - `fd_close` (line 1357) removes the number from the table and drops the handle: the host descriptor closes.
  - `fd_renumber` (line 1857) checks both numbers are open, closes `to` through `fd_close`, and moves `from`'s descriptor to `to`. So it frees one descriptor and moves another; it never makes one.
  - `sock_accept` (line 2642) is "not implemented" in preview1 and answers `ENOTSOCK`; and wasmtime-py 49.0.0's `WasiConfig` has no socket preopen at all (EXECUTED: its public names are `argv`, `env`, `inherit_*`, `preopen_dir`, `stdin_file`, `stdout_*`, `stderr_*`).
  - `fd_readdir` (line 1948) opens a directory stream and deletes it from the table within the same call: a descriptor that never outlives one host call. The other path calls open nothing that survives their call.
  - Preview1 has no `dup`.
- **The guest's binaries import `path_open` and `fd_close`, not `fd_renumber`** (EXECUTED, `imports068.py`, `imports.txt`: the 42 preview1 imports of `python.wasm` and `python-snapshot.wasm` are the same, `fd_renumber` absent, `sock_accept` present). Spec 032 already noted that `fd_renumber` is not imported and shadowed it in the mount linker so a later binary cannot reach a provider number unseen.
- **One host descriptor per open file or folder in a grant; none for a mount** (EXECUTED, `pa_one_descriptor_per_open.txt`). A door host counted this process's descriptors while the guest held what it had opened: +100 after 100 files, +250 after 250, +300 after 50 folders more, +0 once it had closed them all. With a mount beside the grant, 200 files opened in the mount added 0: a mount's file is staged bytes in the runner's table (`_Open.data`), served by the provider, and its preopen is an empty placeholder folder (READ, `mounts.py`, `_Files`, spec 032).
- **The stdio streams and the preopens** are made by the runner before the guest runs (READ, `runner.py`, `_instance`: `stdin_file`, two custom outputs, one `preopen_dir` per grant, mount and the stdlib). Their number is fixed by the embedder's arguments, not the guest.
- **What the guest sees at exhaustion today is `EIO`, not `EMFILE`** (EXECUTED, `pb_errno_today.txt`): under a soft limit of 256 the guest opened 245 files, then got errno 29 (`EIO`, "I/O error"); the guest's `errno.EMFILE` is 33. wasmtime maps an OS error it does not list to `ErrorCode::Io`, and `EMFILE` is not in its list (READ, `crates/wasi/src/filesystem.rs`, `from_raw_os_error`, lines 388 to 469).
- **wasmtime 49.0.0, not 49.0.3.** The clone is 49.0.3. Its `RELEASES.md` lists what 49.0.1 to 49.0.3 fixed; none touches `path_open`, `fd_close` or `fd_renumber` (the preview1 items are `fd_readdir`'s padding, `path_rename`'s trailing slash, preview0's `poll_oneoff` and the set-times panic) (READ). Every EXECUTED fact here ran on wasmtime-py 49.0.0, which embeds 49.0.0.

## 3. How to count (READ, INFERRED)

- **wasmtime-py offers no hook.** No preview1 table limit exists in its `WasiConfig` (above); `Store.set_limits` bounds WebAssembly tables and memories, not WASI's descriptor table; the runner cannot set a per-store `RLIMIT_NOFILE`, which is per process. Counting host descriptors from the host side (`/dev/fd`, `/proc/self/fd`) would be per process, racy between concurrent calls, and different on Windows, which constitution §4.3 rules out.
- **The runner already shadows the right calls.** Every call has a `_Files` table since spec 048 (READ, `runner.py`, `_instance`). A call with mounts runs on the mount linker, which shadows 29 calls, `path_open`, `fd_close` and `fd_renumber` among them, and forwards any call on a number that is not a mount's to wasmtime's own through a trampoline (`_Files.forward`), fuel-neutral: the guest's fuel is read before the forward and set back after it (READ, `mounts.py`, `forward`). A call without mounts runs on the guard linker, which shadows `fd_readdir` and `path_rename` only (spec 048), served by the same `_Files` class with no mounts.
- **So counting needs no new import, no guest change and no build step** (INFERRED). The guard linker shadows three more calls, `path_open`, `fd_close` and `fd_renumber`, which the table already serves by forwarding when the number is not a mount's. The table keeps the set of wasmtime numbers the guest opened and still holds:
  - a forwarded `path_open` that answers 0 adds the number wasmtime wrote at the result pointer;
  - a forwarded `fd_close` that answers 0 removes its number;
  - a forwarded `fd_renumber(from, to)` that answers 0 removes `to`, then moves `from` to `to` if `from` was held.
  - The stdio streams and preopens are never in the set; closing one frees nothing counted, and a number wasmtime reuses for a later open is counted from that open.
  - A mount's open file is already counted by the table (`opened`, the provider numbers in use).
  - At the call's end `store.close()` drops every descriptor the guest still holds (READ, `_instance`'s `finally`), so nothing carries over to the next call.
  - A `path_open` whose result pointer is out of bounds traps in wasmtime after it has opened the file (EXECUTED on plain wasmtime, `pi_bad_result_pointer.py`, `pi_bad_result_pointer.txt`: `f0` opened as 4, `f1` with the pointer past memory trapped "Pointer out of bounds", and `f2` then opened as 6, so 5 was left held; READ, `p1.rs`: `path_open` returns the number, and a bad pointer is a trap, line 1114's `From<GuestError>`). Under the runner that trap ends the run, and the store's close frees the descriptor. At most one descriptor goes uncounted, for the instant before the run ends.
- **Where the check sits** (INFERRED). For a number that is not a mount's, before the forward: at the cap the runner answers `EMFILE` and wasmtime opens nothing, so the host never holds more than the cap for the guest. That makes `EMFILE` win over every other answer a `path_open` could give, as Linux's `open` allocates the descriptor before it walks the path. For a mount, where the table already answers `EMFILE` past `MAX_MOUNT_FILES` (1,024): after the runner's own path answers, before any provider call, so a refused open spends no file call.

## 4. The prototype, counted (EXECUTED)

`pd_cap.py`, output `pd_cap.txt`, with `prototype068.diff` applied:

| case | result |
|---|---|
| a grant, cap 16, open until refused | 16 opened, then `EMFILE` ("No file descriptors available", wasi-libc's text) |
| close one, open one, open another | the open after the close succeeds; the next is `EMFILE` |
| `os.listdir` at the cap; a missing file at the cap | both `EMFILE` |
| close all, open 16 again | 16 opened |
| 8 folders and 8 files, cap 16 | the 17th open (a folder) is `EMFILE` |
| 10 mount files and 6 grant files, cap 16 | the next grant open and the next mount open are both `EMFILE`; the provider was asked 10 `read`s, none for the refused open; closing a mount file lets a grant file open |
| cap 1,024, open until refused | exactly 1,024 opened, then `EMFILE`; the run goes on and exits 0 |
| no cap (`None`) | 3,000 opened |
| cap 0, snapshot | `print(1)`, `import json` and `import csv` all run: the snapshot holds them |
| cap 0, plain reactor | exit 1, "Fatal Python error: Failed to import encodings module": the zip cannot be opened |
| cap 1 and 2, plain reactor | `import json, csv, decimal` runs: the zip is opened one read at a time |
| cap 4, two calls in a row, each holding 4 at exit | each holds 4: nothing carries over |

Every run that met the cap ended `exit_code` 0 with `trapped` `None`: `EMFILE` is an answer the guest's libc handles, not a stop.

## 5. What it costs (EXECUTED)

- **Fuel: nothing.** `pe_fuel_exact.py` (output `pe_fuel_exact.txt`) gives the runner's linker a fixed `random_get` and a counting `clock_time_get`, the clock-and-random memo's method, so a program's fuel is the same on every run; then it switches the three counted shadows off (`mounts.COUNTED = ()`, main's guard linker) and on, three times each, in one process. A fixed file-heavy program (50 CSV files read, 2,000 open-and-close pairs, two listings; with a mount, 20 provider files read too):

  | binary | place | shadows off | shadows on | delta |
  |---|---|---:|---:|---:|
  | snapshot | grants | 111,512,532 | 111,512,532 | 0 |
  | snapshot | grants and a mount | 113,321,812 | 113,321,812 | 0 |
  | plain | grants | 331,685,363 | 331,685,363 | 0 |
  | plain | grants and a mount | 333,493,998 | 333,493,998 | 0 |

  Each cell was the same in all three runs. The forward sets the guest's fuel back after wasmtime's call, and a host function spends no fuel of its own (READ, `forward`). Without the fixed clock and random source, the same program's fuel moved by up to 0.08% between three runs on main alone (`pc_cost.py`, `pc_cost_main.txt`), so only the fixed form can show a delta.
- **The judge: nothing moves.** The fast tier, `uv run pytest -m "not slow" -n 3`, on main (`fast-baseline.log`) and with the prototype (`fast-prototype.log`):

  | | main | prototype |
  |---|---|---|
  | scoreboard | 351/416 pass, 0 fail | 351/416 pass, 0 fail |
  | v1.4 embedding | 162/162 | 162/162 |
  | ratchet | lost 0, grew 0 | lost 0, grew 0 |
  | unit suite | 1,223/1,231 | 1,222/1,231 (1 failed) |

  The one failure is spec 048's unit `test_a_guard_call_leaves_the_other_calls_native`, which asserts that the guard linker shadows exactly `fd_readdir` and `path_rename`. It fails by design: the guard linker now shadows five calls. The specification changes that assertion, as a stated judge change. The fuel ratchet compares every metered check's fuel within 0.01% (READ, `tests/harness/scoreboard.py`, `FUEL_TOLERANCE`); none grew. The full judge with the prototype, once, `uv run pytest -n 3` (`full-prototype.log`): 363/416 pass, 2 gap, 51 blocked, 0 fail; v1.4 162/162; `ratchet vs 2ce08a592d: lost 0 · absent 0 · unrun 0 · unrun locally 37 · gained 0 · grew 0`; the same one unit failed. The 51 blocked are the worktree's missing source trees and artifacts other than the set (the upstream suites among them), not the prototype. The slow tier's guest jobs run on the judge's own driver, not through `run`, so they never meet the cap (READ, `tests/harness/guest.py`).
- **Host CPU: about 50 µs per open-and-close pair, on calls without mounts** (`pf_host_cpu.py`, `pf_host_cpu.txt`; one process, the shadows off and on alternately, ten rounds each; the guest times 20,000 pairs with its own clock, which is the host's):

  | | open and close, median | `os.stat` control, median |
  |---|---:|---:|
  | shadows off (main) | 39.9 µs | 25.0 µs |
  | shadows on | 91.8 µs | 28.1 µs |

  So about 52 µs more per pair (an earlier run on a busier machine: 60 µs), about 26 µs per shadowed call: the shared host function, the table's dispatch and the trampoline's forward through ctypes, the same path every grant call of a call with mounts already takes (spec 032). The control, which the shadows do not touch, did not move beyond noise.
- **Per run** (`ph_opens_per_run.py`, `ph_opens_per_run.txt`, counting the table's dispatch):

  | binary | program | `path_open` | `fd_close` |
  |---|---|---:|---:|
  | snapshot | `pass` | 0 | 0 |
  | snapshot | `import json, csv, decimal, pathlib` | 0 | 0 |
  | snapshot | pandas reads a 1,000-row CSV and groups it | 3 | 3 |
  | plain | `pass` | 7 | 7 |
  | plain | `import json, csv, decimal, pathlib` | 57 | 57 |
  | plain | the pandas program | 919 | 919 |

  The snapshot, the default, pre-imports the stack, so a typical call makes a handful of opens: well under a millisecond added. The plain reactor reads each module from the zip with its own open: importing pandas there took a median of 998 ms with the shadows off and 1,147 ms with them on (six rounds each, `pf_host_cpu.txt`), about 15% more.
- **A cheaper way was looked for and not found** (INFERRED). Shadowing `path_open` alone, and finding closed numbers by asking wasmtime (`fd_fdstat_get`) for every held number when the cap is reached, halves the cost per pair; but a guest that holds the cap and keeps opening would make the host sweep 1,024 numbers per refused open, about 25 ms each, for as long as the deadline allows. The exact count needs `fd_close`. A cheaper forward for every shadow (mounts included) would be a separate change to the trampoline.
- **No check comes near 1,024.** The prototype logged each call's peak count of open files and its refusals (`peaks-summary.txt`). In the fast tier, 1,180 calls: no refusal; the highest peaks were 1,024 in spec 032's `test_mount_descriptors_are_bounded` (1,025 mount opens, refused at 1,024 by `MAX_MOUNT_FILES`, which the cap meets at the same count), 241 in `test_a_guest_that_uses_up_host_descriptors_cannot_make_run_raise` (a child whose soft limit is 256 runs out first, and its guest gets `EIO` as today), and 6 or fewer everywhere else (951 calls held none). The full judge's calls through `run` are the same 1,180, with the same peaks.
- **The raw rows of criteria 1 and 2 hold on the prototype** (`pg_raw_rows.py`, `pg_raw_rows.txt`, through the judge's own `Guarded` and `Mounted` harnesses with `table.open_files` set): three opens, then `EMFILE` with 3 forwards; a close frees one; a failed open holds nothing; closing a never-opened number or stdin frees nothing; renumbering moves and frees as wasmtime does; with a mount, the fifth open of either kind is `EMFILE` and the provider saw 2 reads. One row differs from plain wasmtime: the prototype's guard table answers `fd_renumber(2**31 - 1, 2**31 - 1)` with `ENOTSUP` (58), wasmtime with `EBADF` (8), because the mount table's rule for provider numbers applies; the specification limits that rule to tables with mounts.

## 6. How it meets the other limits (READ, INFERRED)

- **`max_file_calls`** (spec 032) counts provider calls, for mounts only, and ends the run past it, because a file call cannot be refused without breaking the guest's libc. A refused open makes no provider call, so it spends no file call; and an open past the cap can be refused cleanly with `EMFILE`, so the run goes on. The two are independent.
- **`MAX_MOUNT_FILES`** (1,024, spec 032) bounds a mount's provider numbers per call, owed write-backs included. If the cap counts mount files too, the default cap and the constant agree; with a larger cap, or none, the constant still bounds a mount's files.
- **The staging bound** (`memory_bytes`) bounds a mount file's bytes, not their number.
- **Should mount files count?** They hold no host descriptor (§2). Counting them anyway makes "files open at once" mean the same whatever serves a path: the guest sees one number for its files, and an embedder who lowers the cap to shrink what one sandbox holds lowers it for mounts too (each open mount file holds a table entry and its staged bytes on the host). Counting them costs nothing new: the table already keeps `opened`. Not counting them would let a guest hold 1,024 mount files and 1,024 grant files under a cap of 1,024 (INFERRED).
- **Sessions** (spec 055, confirmed, not built). A session keeps its store and its `_Files` table across turns (its Decisions 6, 7 and 11), so descriptors a turn leaves open stay open. The count therefore belongs to the session, not the turn: a per-turn allowance would let each turn open the cap again on top of what earlier turns hold. 055 resets only the table's per-turn counters (`calls`, `faults`, `refused`, `refused_total`).
- **Concurrent calls.** The cap is per call (per session). An embedder running N calls and sessions at once can still hold N times the cap, plus each call's preopens and stdin; the process's `RLIMIT_NOFILE` should exceed that (INFERRED). The README should say so.

## 7. The public names (READ)

- The existing pairs: `max_file_calls=` and `Defaults.file_calls`; `max_tool_calls=` and `Defaults.tool_calls`; `max_tool_request_bytes=` and `Defaults.tool_request_bytes` (spec 060, the most recent). So: **`max_open_files=`** and **`Defaults.open_files`**.
- The command line has `--deadline-s`, `--memory-bytes`, `--output-bytes` and `--fuel`, each one of `run`'s arguments; spec 054 added `--import-path`. The command takes `--grant`, `--grant-writable` and `--root`, so its guests open host files; without a flag, a command user whose program needs more than 1,024 files at once would have no way to raise the new default. Spec 049, Decision 8 lets a minor release add command options.
- Spec 049, Decision 8: a new limit with a default is "a tighter default" (exception 1, a Changed line); it also closes a documented hole (the a2 review's F11, spec 055's F2), so exception 2 applies too, as spec 060 used both.

## What the specification should decide

A per-call (per-session) count of the files and folders the guest holds open, grants and mounts alike, kept by the call's `_Files` table, with `path_open`, `fd_close` and `fd_renumber` shadowed in the guard linker; `EMFILE` before wasmtime or the provider is asked; default 1,024; `max_open_files=`, `Defaults.open_files` and `--max-open-files`; per session in a session; no record field.

## Addendum after the pre-build review (2026-10-18)

The review (written in the coordinator's scratchpad, for the lane to copy to `../reviews/068-a-cap-on-open-files-spec-2026-10-18.md`, with its probes) confirmed §2 to §5: the count is exact against wasmtime's own table (its `r1_accounting`), the fuel delta is 0 to the instruction (`r3`), and the host CPU is 54.5 µs per pair (`r4`). It added two facts this memo had missed, and one that came after it.

- **The cap sits on top of the process's own descriptors** (the review's F1, EXECUTED there, `r2_default_vs_soft_limit`). The process holds about eleven before the guest opens anything. Under a soft limit of 256 (macOS's default for a process launchd starts) the guest opened 245 and got `EIO`; under 1,024 (Linux's usual) it opened 1,013 and got `EIO`; in both the door host's `open()` failed with `EMFILE`. Under 1,060 and 2,048 the guest opened 1,024, got `EMFILE`, and the door host's `open()` succeeded. This machine's shell had raised its own soft limit to 1,048,576, which is why §1's 122,870 (`kern.maxfilesperproc` less what the process held) appeared; macOS's default is 256 (`launchctl limit maxfiles`). §6's "Concurrent calls" understated it: one call needs the room too.
- **A process may raise its own soft limit to its hard limit** (EXECUTED here, `pj_raise_soft_limit.py`, `pj_raise_soft_limit.txt`): from 256, macOS accepted the unlimited hard limit, 10,000,000, 1,048,576, 122,880 and 10,240 alike. The kernel then holds a process at `kern.maxfilesperproc`. So the command, which owns its process, can make its default cap effective with one `setrlimit` call.
- **Path calls hold one descriptor per folder while they resolve** (the review's F2; READ there, cap-primitives 4.0.3's `fs/manually/open.rs`; EXECUTED there, `r8_path_depth`). On macOS, and on Linux without `openat2`, cap-std walks a path one component at a time and keeps each parent folder's descriptor for the length of the call. §2's "a descriptor that never outlives one host call" holds, but "one" does not: a 900-deep path took the process from 4 descriptors to 912 during `os.stat` calls with no file held open; under a soft limit of 512 and a cap of 8, the guest held the process at its limit and an embedder thread's `open()` failed 476 times. The cap does not count these; spec 068 states it, and spec 072, a bound on path depth, would close it.
- **Decision 34** (main `4a94c14`, after this memo's base): the snapshot pre-imports no package. After spec 069 the snapshot imports pandas from the zip as the plain reactor does in §5's table: 919 opens and closes, about 50 ms of host CPU added. And spec 048's unit `test_a_call_without_mounts_is_unchanged` would then see `path_open` and `fd_close` served for `import json` (the review's `r6_unchanged_unit_after_069`); 068 changes it.
