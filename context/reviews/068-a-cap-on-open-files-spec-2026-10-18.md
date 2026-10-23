# Review of 068 — A cap on files open at once (the specification, before build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of the spec, the memo, the prototype or the code. I read `AGENTS.md`; the constitution (§4.3, §4.15, §5.2, §5.6); `decisions.md` (question 92, and Decision 34, which main gained after 068's base); specs 032, 034, 048 (its criterion 5 unit), 049 (Decisions 7, 8, 10, 13), 054, 060 and its pre-build review (for the format); 055 both as on main and as revised on `spec/055-bounded-sessions` at `ddc3fff`; and the code the spec changes (`mounts.py`: `GUARDED`, `_Files.__init__`, `forward`, `__call__`, `_take`, `_drop`, `_fd_close`, `_fd_renumber`, `_path_open`; `runner.py`: `Defaults`, `_integer_limit`, `_instance`, `_shared`, `_Call.stop`, the three linkers; `cli.py`; `tests/harness/files.py`; the units of `tests/unit/test_runner_mounts.py` named below; `tests/public_api.txt`). I read wasmtime 49's `crates/wasi/src/p1.rs` (`Descriptors`, `fd_close`, `fd_renumber`, `path_open`) and cap-primitives 4.0.3, the version wasmtime 49's `Cargo.lock` pins (`fs/manually/open.rs`, `rustix/linux/fs/open_impl.rs`, `stat_impl.rs`). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/068-a-cap-on-open-files` at `d256237`, on main `434a811` (`git diff 434a811..d256237`): the spec, the memo `research/2026-10-18-a-cap-on-open-files.md`, its probes and `prototype068.diff`. The diff touches only `context/` (READ).
- **Ran (EXECUTED, darwin-arm64, CPython 3.14.2, wasmtime-py 49.0.0, the frozen set `build/sets/s-4eb5418a2b1bb553-c353b1d9`, read only).** Nothing was written in either git tree. The prototype was applied to a scratch copy (`git archive d256237` plus `git apply prototype068.diff`, its own `.venv`). Scripts and outputs are in `probes/` beside this file:
  - `r0_host_limits.txt`: this shell's soft limit (1,048,576), `launchctl limit maxfiles` (256 soft, unlimited hard: macOS's default for a process launchd starts), `kern.maxfilesperproc` (122,880).
  - `r1_accounting.py` → `.txt`: the prototype's count against wasmtime's own table, through renumber chains, preopens, stdio, double closes, `O_CREAT`/`O_TRUNC` at the cap, the bad-pointer trap, and a closed mount preopen whose number is reused.
  - `r2_default_vs_soft_limit.py` → `.txt`: the default cap of 1,024 under soft limits of 256, 1,024, 1,060 and 2,048, with a door host that opens a file.
  - `r3_pe_fuel_exact_rerun.txt`, `r4_pf_host_cpu_rerun.txt`: the memo's `pe_fuel_exact.py` and `pf_host_cpu.py`, re-run unchanged on the scratch copy.
  - `r5_renumber_self_mutant.py` → `.txt`: `fd_renumber(a, a)` on the prototype, and on a mutant without the spec's `from != to` test.
  - `r6_unchanged_unit_after_069.py` → `.txt`: what the shadows serve for `import json`, on the snapshot and on the plain reactor (standing in for the snapshot after spec 069).
  - `r7_fast_tier_prototype.txt`: the fast tier on the scratch copy with the prototype.
  - `r8_path_depth.py` → `.txt`: transient host descriptors from one path call on a deep path.
  - `ref_055_pb_fd_exhaust.txt`: a copy of spec 055's review probe output, for the 122,870.

## What holds

- **`path_open` is the only call that makes a descriptor the guest keeps (READ).** In p1.rs only `path_open` (line 2210) and `Descriptors::new` (stdio, preopens) call `push`. `fd_close` frees a number into `free`; `fd_renumber` closes `to` through its own `fd_close` and moves `from`; preview1 has no `dup`; `sock_accept` makes nothing. So shadowing `path_open`, `fd_close` and `fd_renumber` is complete for preview1.
- **The count is exact against wasmtime's table (EXECUTED r1).** On the `Guarded` harness with the prototype and a cap of 3: three opens (two files, one folder) then `EMFILE`; at the cap `O_CREAT|O_EXCL` of a new name answers 33 and creates nothing, and `O_TRUNC` answers 33 and leaves the file's 4 bytes; `renumber(a, b)` and then `renumber(b, c)` (a chain) bring the count from 3 to 1; a double close answers `EBADF` and moves nothing; a held number moved onto a preopen stays counted, and closing it frees one; stdin moved onto a held number frees one; closing stdout twice frees nothing; numbers wasmtime reuses (4, 7) are counted from the open. At the end, wasmtime's open numbers were `[2, 3, 5, 6, 7]` and the held set `[5, 6, 7]`: stderr and the preopen not counted, every guest-opened number counted, nothing else. On the `Mounted` harness, a closed mount preopen drops out of the table, its number (3) comes back from wasmtime for a grant open and is counted; a renumber onto a mount file answers `ENOTSUP`.
- **No other route adds an uncounted descriptor the guest keeps (READ, INFERRED).**
  - A mount never forwards `path_open`: `_path_open` with a table entry answers itself or calls the provider. There is no fall-through.
  - An open that fails after the host opened: wasmtime pushes the descriptor right after `open_at`, and `push` fails only when 2**32 numbers are in use (p1.rs, `unused`).
  - The bad result pointer (EXECUTED r1, as the memo found): one descriptor stays in wasmtime's table uncounted (`[0, 1, 2, 3, 4]`, held `[]`). Under `run`, the forward's trap reaches `_shared`, which calls `_Call.stop`: `stopped` is set and the epoch deadline is 0, and every later shadowed call answers `EIO` without forwarding (READ). So no second open can follow, and `store.close()` frees it. The spec's "nothing to handle" is right.
  - Threads: there are none in the guest. Every table belongs to one call; `_shared` serves only the call on top of this thread's stack whose context matches; tools, gates and the async loop never touch `_Files` (READ). A door host that calls `run` again gets a new table with its own cap: the embedder's choice, not the guest's.
- **Fuel: the delta is exactly 0 (EXECUTED r3).** The re-run gave the memo's four rows to the instruction (111,512,532; 113,321,812; 331,685,363; 333,493,998; off and on, three times each). It is so by construction: a host function spends no fuel, the `call` that reaches it costs the same whatever the callee is, and `forward` sets the fuel back in a `finally` (READ).
- **Host CPU: confirmed (EXECUTED r4).** 54.5 µs added per open-and-close pair (memo: 51.9); the plain reactor's `import pandas` 857 → 964 ms median, +12.5% (memo: +15%).
- **The rejected cheaper design is rightly rejected (INFERRED).** Without an `fd_close` shadow the table cannot learn of a close. So at the cap it must sweep every held number (about 25 ms per refused open), or refuse wrongly, or rate-limit the sweep. A sweep is host CPU that fuel does not see: a metered call with no deadline could loop refused opens and spend 1,000 times its fuel's worth of host time. Exactness, and an `EMFILE` that frees at once on a close, are worth 26 µs per call. The cost to cut is the forward itself, which the Scope rightly leaves to its own change.
- **The rule and its place are right.** Checking before the forward means wasmtime opens nothing and creates nothing (r1). For a mount, checking beside `MAX_MOUNT_FILES` keeps spec 032's order of answers and spends no file call (the memo's `pd_cap.txt`: 10 reads for 10 opens).
- **The public names follow the house pattern (READ).** `max_open_files=` / `Defaults.open_files` sit beside `max_file_calls` / `file_calls` and `max_tool_request_bytes` / `tool_request_bytes`. `int | None`, checked by `_integer_limit`, placed last in `run`, `run_async` and `Defaults`. The five snapshot lines and the rules cited are right: a new keyword whose default does not keep today's behaviour needs exception 1 or 2. Both are cited, and both CHANGELOG lines are written, which is what 060's review asked of 060 (its F5). Inserting `--max-open-files` after `--fuel` is fine: spec 054 inserted `--import-path` mid-list.
- **The default of 1,024 against the mount table's own 1,024:** they coincide at the default. With a larger cap `MAX_MOUNT_FILES` still bounds mount files, and the README text in Decision 13 says so. The fast tier's highest peak (1,024, spec 032's check) is that very coincidence, refused by the constant (the memo).

## Acceptance criteria against the design

1. Sound in shape, and its stand-ins (a) to (h) are each caught (READ). Two renumber rows are missing, and one missing row hides a bypass (F4).
2. Sound. Stand-ins (i) to (k) are caught.
3. Sound for `run`. `run_async` is checked for validation only, not for passing its value (F8).
4. Sound. Its guest must import everything it needs before it fills the cap once spec 069 lands (F3).
5. Sound on POSIX hosts. On Windows it skips the cap's count, which it could still check, and it does not say what happens when the hard limit is below 2,048 (F8).
6. and 7. Sound. 7 is a judge change that names one of the three judge texts it falsifies (F6).
8. to 10. Sound. 8's "no existing judge file is edited but …" must grow by F3 and F6.
11. Written against the wrong 055 (F5).

## Findings, most severe first

1. **F1. At its default, on a stock macOS or Linux host, the cap does not guard the host process: the host still runs out first. High; write in, and tell the owner.** (Intent; Decisions 5, 7, 13; EXECUTED r0, r2.)
   - The guest's descriptors share the embedder's process table. The process already holds about 11 before the guest opens anything. So a cap of 1,024 protects only where the soft `RLIMIT_NOFILE` is above about 1,035, plus each call's preopens, times the calls and sessions open at once.
   - r2, with the prototype at 1,024 and a door host that opens a file after the guest has filled up:

     | soft limit | guest opened, then | door host's `open()` |
     |---|---|---|
     | 256 (macOS's launchd default) | 245, then `EIO` (29) | `EMFILE` |
     | 1,024 (Linux's usual: login shells, systemd services, recent container runtimes) | 1,013, then `EIO` | `EMFILE` |
     | 1,060 | 1,024, then `EMFILE` (33) | ok |
     | 2,048 | 1,024, then `EMFILE` | ok |

   - So on the two most common default configurations, nothing changes from today. The guest sees `EIO`; another call's `run` and the embedder's own code can fail with `EMFILE`. The spec's Intent ("So one guest can no longer take the descriptors the embedder's process needs"), Decision 5's reason ("Linux's usual soft limit, so a program … meets the same limit": but there the 1,024 includes the process's own descriptors, here it is on top of them) and Decision 7 ("the command's own process is the host here, so the default already guards it") are each false at those defaults. Decision 13's *Not protected* text says to raise `RLIMIT_NOFILE` only "where many run at once"; one call needs it too.
   - Criterion 5 passes only because its child sets 2,048 first. That is correct for the check, but it hides the fact.
   - **Fix (spec text, no new mechanism needed to build):**
     - State the fact in the Problem and in Decision 5, with r2's table.
     - Make the README's *Safety* say it in plain words: the cap keeps a guest from starving the process only when the process's soft descriptor limit is above the cap plus what the process holds, for every call and session open at once. macOS starts processes at 256 and many Linux setups at 1,024, so raise the soft limit (for example `resource.setrlimit(RLIMIT_NOFILE, (hard, hard))` at start, as the Go runtime does for every Go program since 1.19), or lower `max_open_files` below it.
     - Correct Decision 7. Either the command raises its own soft limit towards its hard limit at start (it owns its process; one call to `resource.setrlimit`, nothing on Windows), or its help and the README say `ulimit -n`.
   - **For the owner, in one line** (§5.2: the spec still decides; this does not block the build): the default of 1,024 was chosen without this fact. The options are to keep it with the text above, have the runner raise its own process's soft limit when the hard limit allows (a library touching process state, so the owner's call), or choose a default below common soft limits (a tighter default, which §4.15 does not require the owner for, but the owner named 1,024). Recommended: keep 1,024, write the text, and record the question.

2. **F2. Transient descriptors are not "at most one per call in flight": on macOS one path call holds one host descriptor per path component, uncounted, and a guest under a cap of 8 exhausted a 512-descriptor process this way. High (macOS, and Linux without `openat2`); write in, as a stated limit and a follow-up.** (Decision 1's "Not counted"; Scope's "Descriptors wasmtime opens inside one host call"; Decision 13's *Not protected* "one descriptor at a time inside a listing"; READ cap-primitives 4.0.3; EXECUTED r8.)
   - READ: wasmtime 49 resolves every guest path through cap-std. Off Linux, cap-std's `manually::open` and `manually::stat` walk the path one component at a time and push each parent folder's descriptor on a stack: "We hold onto all the parent directory descriptors so that we don't have to re-open anything when we encounter a `..`." On Linux 5.6 and later, `openat2(RESOLVE_BENEATH)` resolves in one call and holds one descriptor. Without `openat2` (an older kernel, or a seccomp profile that answers `ENOSYS`), Linux falls back to the manual walk.
   - So every path call holds about as many descriptors as the path has folders, for the length of the call: `path_filestat_get`, `path_create_directory`, `path_unlink_file`, `path_rename`, and `path_open` below the cap. None of them is counted or refused by the cap. A writable grant lets the guest make the tree as deep as it likes.
   - EXECUTED r8, with the prototype's cap set to **8**. The guest builds `/w/d/d/…` in a writable grant, then calls `os.stat` on the bottom in a loop. A sampler thread counts the process's descriptors, and an embedder thread calls `open()` every 0.5 ms:
     - Soft limit 1,048,576, depth 900: the process went from 4 descriptors to a peak of **912**, with no file held open by the guest. The run hit its 300 s deadline inside the loop: about 900 `openat`s per stat.
     - Soft limit 512, depth asked 800: `mkdir` itself stopped at depth 501 with `EIO`, and every stat failed. The process sat at its limit (peak 512). **The embedder thread's `open()` failed with `EMFILE` 476 times** (152,403 succeeded). The guest exited 0.
   - So on macOS a guest under any cap can still hold the process at its descriptor limit, from one call, for as long as its deadline lasts. It is the very failure the spec closes for `path_open`, through the side door of path resolution. **Severity: High on macOS and on Linux without `openat2`; nothing on Linux 5.6+ (INFERRED from the READ above; not run on Linux here).**
   - **Fix:**
     - Correct the three texts. A listing's stream is one descriptor, but a path call holds up to one per folder in its path, on macOS and on Linux without `openat2`.
     - In *Not protected*, say that the cap counts the files and folders the guest holds open, not the descriptors wasmtime holds inside one call while it resolves a deep path. Say that on macOS a guest with a writable grant can therefore still bring the process to its limit for the length of a call.
     - Record the closer as its own specification, before 0.1.0 if the owner's "the cap guards the host process" is to hold on macOS. Bounding these descriptors needs a limit on path depth (components after normalisation) on every path call, or on folder creation in grants. The guard linker would then shadow every path call, at about 26 µs each. That is too large a change to fold in here unasked, and too real to leave unnamed.
     - Add r8's peak, for a fixed depth, to criterion 9's benchmark facts. Optionally, add a gap entry naming the follow-up, so the scoreboard carries it.
     - This also bears on F1's advice: raising the soft limit makes the cap effective against held files, but not against depth on macOS.

3. **F3. Decision 34 (main `4a94c14`, after this base) moves the cost onto the default path and breaks a unit that 068 leaves alone. Medium; write in.** (Decision 2's cost, Decision 6's cap 0, Decision 13's README text, criterion 8; READ `decisions.md` 34; EXECUTED r4, r6.)
   - The owner decided the snapshot pre-imports no package; spec 069 (build-class) follows. After it, the snapshot imports pandas, and probably `json`, from the zip, one `path_open` and one `fd_close` per module, as the plain reactor does today: 919 opens for pandas.
     - Decision 2's "a typical call on the snapshot opens 0 to 3 files" and the README's "the snapshot's typical call opens a handful of files" become false. The added host CPU on a pandas script becomes about 50 ms (r4, 54.5 µs × 919), on top of an import that 069's research puts at 4.63 G fuel. That is a few percent of the call. I judge it acceptable, but the spec should say so honestly, either order.
     - Decision 6's "0 refuses every open … The snapshot still runs what it pre-imported" then means only the bootstrap.
     - Any guest check that fills the cap and then imports a module from the zip will get `ImportError` (`EMFILE`). Criteria 4 and 5's guests must import first.
   - **A unit breaks.** `test_a_call_without_mounts_is_unchanged` (spec 048's update of 032's) asserts that the shadows served for `run(["-c", "import json; …"])` are a subset of `{"fd_readdir", "path_rename"}`. Under 068 it passes only because today's snapshot holds `json`. EXECUTED r6 with the prototype: snapshot → `served=[]`; plain reactor → `['fd_close', 'path_open']`, not a subset. So whichever of 068 and 069 lands second meets a red unit caused by 068.
   - **Fix:** rebase onto `4a94c14`. Add a sentence to Decision 2 on 069 (either order), and make the README cost text independent of pre-imports ("one open and one close per module imported from the zip, about 50 µs each pair on an arm64 Mac"). Change that unit now, in this judge change: its assertion to `<= set(GUARDED + COUNTED)`, and its docstring. Name it in Decision 8 and criterion 8. Write "import before filling" into criteria 4 and 5. Record the cheaper forward (Scope) as a follow-up on the roadmap, because after 069 it touches every default call that imports.

4. **F4. Criterion 1 cannot see a renumber of a number onto itself, and that mutant is an unbounded bypass. Medium; write in.** (Decision 2's renumber rule; criterion 1; EXECUTED r5.)
   - The spec's rule is right: "with `from != to`". wasmtime answers 0 to `fd_renumber(a, a)` and keeps `a` (p1.rs, line 1871). A build that drops the `from != to` test discards `a`, finds it no longer held, and drops it from the count.
   - EXECUTED r5, cap 3, each open followed by `fd_renumber(n, n)`: the prototype stops at 3 opens (count 3). The mutant opens all 50 (count 0).
   - No row of criterion 1 renumbers a held number onto itself: its only `a == b` row is `(2**31 − 1, 2**31 − 1)`, an unheld number that answers `EBADF`. No binary imports `fd_renumber` today. But the call is shadowed precisely for a later binary, and the raw harness reaches it.
   - A second gap, smaller: no row renumbers an unheld `from` (stdin, a preopen) onto a held `to`. A build that discards `to` only when `from` is held passes criterion 1, and its count drifts high: it refuses wrongly, but nothing is unsafe.
   - **Fix:** add two rows and two stand-ins. (t) `fd_renumber(a, a)` of a held `a` answers 0, and an open at the cap still answers `EMFILE`; the mutant without `from != to` lets it open. (u) `fd_renumber(0, a)` of a held `a` answers 0 and frees one (the next open answers 0); the mutant that drops `to` only when `from` is held answers `EMFILE`.

5. **F5. The 055 hand-off is written against main's 055, not 055's revision, and the two disagree. Medium; write in.** (Decision 9, criterion 11; READ 055 at `ddc3fff` on its branch, and as on main `434a811`.)
   - 055's revision (awaiting re-review) already carries:
     - a Decision 5 bullet for "068's cap on open files" (per session, read at the opening);
     - its own table row ("068's cap on open files | per session"), not a word in the `memory_bytes` row;
     - "plus the cap on open files that 068 adds to `run`, under the name 068 gives it" in the signature;
     - Decision 8: the cap "holds through the session's ending too, so an `atexit` handler that opens files meets it";
     - Decision 11's and 22's paragraphs rewritten to say the cap is 068's;
     - Decision 17's note; and criterion 40, "068 is expected to land first; if it has not, this criterion and Decision 5's 068 bullet move to 068". Criterion 40 uses a cap of 8 and includes the ending's handler.
   - 068's Decision 9 asks 068's branch, if 068 lands first, to add most of that again, worded differently, to main's older text. That would duplicate 055's revision and conflict with it when 055 rebases. If 055 lands first, 068 carries "criterion 11" (a cap of 4, no ending) instead of 055's criterion 40, so the ending case is lost.
   - The substance agrees both ways: per session; read once at the opening; the held set and `opened` never reset; 055 resets only `calls`, `faults`, `refused` and `refused_total` (READ, both). Owed buffers do not survive into a usable turn: a gate refusal at a close ends the session in 055's table (READ). So F7's formula question does not change it.
   - **Fix:** rewrite Decision 9 against `ddc3fff`.
     - If 068 lands first: 068 edits no 055 text but the name. Where 055 says "under the name 068 gives it" and "068's cap on open files", 055's builder writes `max_open_files` and `Defaults.open_files`. The lane tells 055's branch, or 068 does it on main if 055's revision is on main by then.
     - If 055 lands first: 068 carries 055's Decision 5 bullet and its criterion 40 as 055 wrote them, the ending's handler included, and drops its own criterion 11.

6. **F6. The stated judge change names one of three judge texts that 068 makes false. Low; write in.** (Decision 8, criterion 8; READ.)
   - `test_a_guard_call_leaves_the_other_calls_native`: named, and its docstring ("every other descriptor call (path_open, …) reaches wasmtime without passing the guard table") must change too. The spec says so.
   - `test_a_call_without_mounts_is_unchanged`: its docstring ("whose only shadows are fd_readdir and path_rename") and its assertion (F3). Not named.
   - `tests/harness/files.py`, `Guarded`'s docstring ("but for the two calls the guard shadows"). Not named.
   - In `src/`, for the Design list: `mounts.py`'s module docstring (line 24, "shadows only the two calls in `GUARDED`"), the comment above `GUARDED` ("A call without mounts shadows these two only"), and `_guard_linker`'s docstring.
   - **Fix:** name all of them in Decision 8 and criterion 8, with the reason.

7. **F7. Two small design choices. Low; write in.** (Decision 6, Design; READ.)
   - `_instance` would read `c.get("open_files")`, so a `c` without the key runs uncapped. No caller builds `c` by hand: only `_checked` makes it, and `_instance` reads `c["file_calls"]` strictly. The `get` only fails open, for example if 055's `Session` forgets the key. Use `c["open_files"]`. The tables the harness builds by hand do not pass through `_instance`.
   - The spec's count is `len(held) + opened`, but the prototype, which made every EXECUTED number, uses `len(held) + opened − len(owed)`. They agree in practice: an owed buffer exists only while a call or session stops (READ, `_write_back`, `_gate`). But the spec and its evidence should agree. Prefer the prototype's: the guest closed those numbers, and POSIX's close frees the descriptor even when the flush fails.

8. **F8. Three criteria gaps. Low; write in.**
   - `run_async`'s value is never shown reaching the table. Criterion 3 checks only that a bad value raises with 0 submits. Add a `run_async` row to criterion 4 (a cap of 2: the third open is `EMFILE`). Stand-in: `run_async` drops the keyword.
   - Criterion 5 skips on Windows, so the 1,024 count is never seen at the default there. Windows runs only in the release workflow (AGENTS.md rule 6b). Run the count rows on Windows without `setrlimit`, as the neighbour runs `NO_RLIMIT`.
   - Say what criterion 5 does when the hard limit is below 2,048: skip with that reason, or fail.

9. **F9. "122,870 on macOS" is this shell's raised limit, not macOS's default. Note.** (Problem; CHANGELOG text; EXECUTED r0.) 122,870 is `kern.maxfilesperproc` (122,880) less what the process held, reached under a soft limit of 1,048,576. macOS starts a process at 256 (`launchctl limit maxfiles`). Write "until the process's own limit (122,870 on the research's Mac)", and F1's table.

## Constitution checks

- **§4.15:** holds in form. A new limit with a default; nothing is loosened. In effect, the default does not reach its goal on stock limits (F1): the README must say so.
- **§4.3:** holds. Counting preview1 numbers is the same on every host. F1's remedies keep that: no default that depends on the host. Raising the command's own soft limit is the one host step, a no-op on Windows.
- **§4.4:** holds. No import, no export, no guest change; the shadows define calls the guest already imports (READ).
- **§4.9:** holds. The criteria count opens, forwards, provider calls and errnos; times are in the memo and criterion 9.
- **§4.10:** holds, with F9's wording and F2's "at most one" claim fixed.
- **§5.2:** holds once F1's choice is written as decided (keep 1,024, with the text), and F5's two branches are re-derived from 055's revision.
- **§5.6:** a pre-build review is not required (no import, export, artifact or recipe change). This one was asked for.
- **049, Decision 13:** holds. The Kind line says "changes the public API", the five lines and their rules are listed, and `--write` and `--accept-judge` are named.
- **AGENTS.md rule 4:** the judge change is stated, but incompletely (F6, F3).
- **Build class:** none. `src/`, `tests/`, `README.md`, `CHANGELOG.md`, and 055's text.

## Scoreboard

The diff touches only `context/`, so the worktree is main's state. I did not run the judge in the worktree, to leave it untouched. Instead I ran the fast tier on the scratch copy *with the prototype applied*, to test the memo's claim that exactly one check fails. The command was `WASI_PYTHON_ARTIFACTS=<the frozen set> uv run pytest -m "not slow" -n 3` (EXECUTED, `probes/r7_fast_tier_prototype.txt`, 6 min 30 s). Result: 1,560 passed, 10 failed, 31 skipped. Ratchet vs `2ce08a592d`: lost 2, grew 0. The fuel ratchet did not move.
- One failure is the prototype's: `test_a_guard_call_leaves_the_other_calls_native`, as the memo says.
- The other nine come from the scratch copy not being a git checkout. They are `test_the_package_is_typed` ("py.typed is not tracked"), `test_manifest_recipes_match_the_tree`, `test_recipe_files_leave_out_benchmarks`, five `test_landing_lane` units and one `test_plugin` unit. They are not the prototype's.
- The memo's own run in the worktree (`fast-prototype.log`) shows the same single failure with nothing else lost.

So the claim stands for today's snapshot. F3 shows it does not stand once spec 069 lands.

## Verdict

**Ready to build once F1 to F6 are written in (F2 as a stated limit plus a named follow-up specification, not a mechanism here); F7 and F8 are a sentence each; F9 is wording.** F1 and F2 should also reach the owner in one line each, since together they mean the owner's "the cap guards the host process" holds at the default only on Linux 5.6+ with a raised soft limit. The mechanism is right and exact: it counts every descriptor the guest keeps, refuses before anything is opened, costs no fuel, and fails as an OS does. Its cost is honest, and the cheaper design is rightly rejected. What is missing is honesty about where it protects: at the default, on a stock Mac or Linux box, the host still runs out first (F1), and path calls hold uncounted descriptors off Linux (F2). Two seams need attention too: one with spec 069 (F3) and one with 055's revision (F5). Criterion 1 also needs the renumber row whose absence lets a bypass through (F4).

## One line

Exact counting in the right place at no fuel cost; but say plainly that 1,024 does not protect a host whose own limit is 256 or 1,024, own up to path-depth descriptors, rebase onto Decision 34, test `renumber(a, a)`, and hand off to 055's revised text.

## Confirmation of 068's revision (addendum to the pre-build review)

- **Date:** 2026-10-18. **Reviewer:** the same fresh agent. I did not write the revision.
- **Reviewed:** `git diff dbf8aad..24bc10d` on `spec/068-a-cap-on-open-files`. That covers the spec, the memo's addendum with `pj_raise_soft_limit.py` and `.txt`, question 100 in `questions-for-the-owner.md`, and the roadmap's follow-ups. I read the full revised spec (saved beside this file as `spec-24bc10d.md`). I also read 055's latest revision `e1ee581` (saved as `055-e1ee581.md`): its Decision 5 bullet, table row, signature, Decision 11's reset rule, owed handling and criterion 40.
- **Base checked (READ):** `dbf8aad` is the draft rebased onto `ef1441b`. `git diff d256237 dbf8aad` touches nothing of 068's; it brings only main's research. Decision 34 (`4a94c14`) is an ancestor of the base.
- Nothing was run again. The revision changes no code, and the one new probe (`pj`) is the author's, read here. Neither git tree was touched.

### Each finding

1. **F1: written in, as the lane ruled.**
   - The Problem carries r2's table and the eleven descriptors the process already holds. Decision 5 drops the "matches Linux's limit" reasoning and says where the cap protects. It keeps 1,024, with reasons.
   - Decision 13 adds the README *Safety* item "The cap needs room in your process's own limit", with the exact `getrlimit`/`setrlimit` lines. *Not protected* now says one call needs the room too.
   - Decision 7: the command raises its soft limit to its hard limit before `run`, skipped where `resource` is absent, a refusal ignored. The library never does.
   - Criterion 6 checks the raise: one call `(4096, 4096)`, none when soft equals hard, exit 0 on `ValueError`, nothing without `resource`. A source rule keeps `setrlimit` out of every other file, with stand-ins (v) to (y). Each stand-in is caught by the row it names (READ).
   - `pj` (EXECUTED by the author) shows this macOS accepts the unlimited hard limit from 256.
   - Question 100 states the fact and the options, recommends no to both, and blocks nothing.
   - The Intent now says "within the process's soft descriptor limit".
   - Correct.
2. **F2: written in, as a stated limit plus spec 072.**
   - The Problem gives r8's numbers. Decision 1's "Not counted" names every path call, "about one per folder", macOS and Linux without `openat2`. The "at most one per call in flight" claim is gone.
   - Scope names 072 with its intent. *Not protected* and the CHANGELOG say it. Criterion 9 records r8's peak at depth 300. The roadmap and question 100 carry it. The memo's addendum corrects its §2.
   - Correct.
3. **F3: written in.**
   - Rebased. Decision 2 describes the cost before and after 069 and accepts it in either order. Decision 6 says what cap 0 keeps after 069.
   - Decision 4 adds "an import at the cap fails too". The README cost text is per module. Criteria 4 and 5's guests import first.
   - `test_a_call_without_mounts_is_unchanged` changes to `<= set(GUARDED + COUNTED)`, with its docstring. The cheaper forward is on the roadmap.
   - Correct.
4. **F4: written in.**
   - Rows (t) and (u), with stand-ins (t') and (u'), and a parity row for `renumber(a, a)`.
   - (t') would let the next open through, as r5 showed. (u') would keep `a` counted, so the next open is `EMFILE`.
   - (u) uses stderr because the earlier rows closed 0 and 1 (READ: rows "`fd_close(0)`" and "`fd_close(1)`"). That is right.
   - Decision 2 explains why `from != to` matters.
5. **F5: rewritten against `e1ee581`. Correct both ways (READ).**
   - 055's revision says what Decision 9 says it says: the bullet at its lines 389–400, the row at 421, the signature at 357, the reset of `calls`, `faults`, `refused` and `refused_total` only at 832, and criterion 40 at 1532 with a cap of 8 and the ending's handler.
   - If 068 lands first: the name only. If 055 lands first: 055's bullet and criterion 40 as written (068's criterion 11), plus one more stand-in.
   - One omission, harmless because "as 055 wrote it" governs: 055's criterion 40 passes `shutdown_s=60` to its ending, which 068's paraphrase in criterion 11 leaves out.
6. **F6: written in.** All three judge texts are named in Decision 8 and criteria 7 and 8, and the source texts are in the Kind line and the Design.
7. **F7: written in.** `c["open_files"]` is read strictly. The count is `len(held) + opened − len(owed)` in Decisions 1 and 2, the Design and the sketch's `_at_cap`.
8. **F8: written in.**
   - Criterion 4 adds a `run_async` row (cap 2) with stand-in (p').
   - Criterion 5 runs on Windows without `setrlimit`, and skips with its reason where the hard limit is below 2,048.
9. **F9: written in.** The Problem, the CHANGELOG and the memo's addendum.

### Anything new that is wrong

Nothing blocks. Three notes, each a sentence the builder may take:

- **N1 (macOS refusals).** macOS's `setrlimit(2)` man page has long said `RLIMIT_NOFILE` refuses `rlim_cur = RLIM_INFINITY` ("use `min(OPEN_MAX, rlim_max)`"). This host (Darwin 25, CPython 3.14) accepted it (`pj`). On a macOS that still refuses, the command would stay at 256 silently, and its default cap would not protect it.
  - Suggestion: after a refused raise, try once more with `min(hard, 10240)` (macOS's `OPEN_MAX`), still ignoring a refusal. Add one row to criterion 6: the first call raises, the second is `(10240, hard)`.
  - Not blocking: the README already tells the user how to raise the limit.
- **N2 (an unbounded loop on Windows).** On Windows, criterion 5's "open until `OSError`" loop has no host limit to stop it. So stand-in (q), and main, run until the default 60 s deadline rather than failing fast.
  - Suggestion: bound the loop (say 3,000 opens), so a regression fails at once with a count.
- **N3 (the CHANGELOG section).** Decision 13 says "the 0.1.0a6 section". a6 has passed its security review (`ef1441b`) and may be tagged before 068 lands.
  - Suggestion: write "the unreleased section (0.1.0a6 today)".

### Constitution checks

Unchanged from the review, and now all hold:
- §4.15: a default for the new limit, and the README says honestly where it protects.
- §4.3: no host-dependent default. The command's `setrlimit` is a step only the command takes, and it is skipped on Windows.
- §4.4: no import and no guest change.
- §4.9: the criteria count, including the `setrlimit` calls.
- §4.10: the 122,870 wording and the transient-descriptor claim are corrected.
- §5.2: F1's choice is decided (keep 1,024, with the text and the command's raise). Question 100 waits on nothing.
- 049, Decision 13: five lines, and the command's raise is noted as behaviour, not a snapshot line.

### Verdict

**Confirmed for build.** All nine findings are written in correctly, with the lane's rulings on F1, F2 and F5. The 055 hand-off matches `e1ee581` in both orders. N1 to N3 are optional sentences, not conditions.

### One line

Every finding is in, and correctly so; build it, ideally with a fallback for a refused raise on macOS, a bounded loop on Windows, and "the unreleased section" in the CHANGELOG.
