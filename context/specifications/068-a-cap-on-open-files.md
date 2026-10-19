# 068 — A cap on files open at once

- **Status:** **landed 2026-10-19** (accepted on `75f03ab` as `debb56d`, history line 67; the build review, `../reviews/068-a-cap-on-open-files-build-2026-10-18.md`, confirmed it; see the Landing notes' last part). Before landing: built 2026-10-18 on `spec/068-a-cap-on-open-files` from `24bc10d` (`ef0882f`; the
  Landing notes); awaiting its build review; it lands after the 0.1.0a6 tag. Before that: confirmed
  for build 2026-10-18 (the review's addendum, "Confirmation of 068's revision": "Confirmed for
  build", notes N1 to N3 optional, all three taken). Drafted 2026-10-18 (`dbf8aad`, rebased onto
  main `ef1441b`); reviewed before build
  the same day (the review, written in the coordinator's scratchpad for the lane to copy to
  `../reviews/068-a-cap-on-open-files-spec-2026-10-18.md`, with its probes; verdict: "ready to
  build once F1 to F6 are written in", F7 and F8 a sentence each, F9 wording); revised against
  all nine findings with the lane's rulings (the section "Disposition of the pre-build review",
  near the end, says where each went). It changes neither
  the guest's imports nor its exports, the artifact set nor the build recipe, so §5.6 does not
  require a review before build; the lane asked one because it adds a limit and a public knob,
  and closes a documented hole.
- **Owner:** Clay Gendron
- **Kind:** runner and docs; **parallel-safe**: `src/` and `tests/` only, with `README.md`,
  `CHANGELOG.md` and this specification (and, in one case, one name in spec 055's text,
  Decision 9). No build-class file: it touches no `scripts/`, `recipes/`,
  `downloads/SHA256SUMS` or workflow, and not the guest. The counting needs no guest change: it
  shadows preview1 calls the guest already imports, on the host (Decision 2). **It changes the
  public API** (spec 049, Decision 13): Decision 11 lists the five snapshot lines it adds and
  the rule that allows each. A judge change: new checks, `tests/public_api.txt` regenerated, and
  three existing judge texts changed (Decision 8). The code: `src/wasi_python/mounts.py`
  (`COUNTED`; its module docstring and the comment above `GUARDED`; `_Files.__init__`,
  `_path_open`, `_fd_close`, `_fd_renumber`), `src/wasi_python/runner.py` (`Defaults`, `run`,
  `run_async`, `_checked`, `_check_places`, `_instance`, `_guard_linker` and its docstring),
  `src/wasi_python/cli.py` (the flag; the command's own soft limit, Decision 7). If 055 has
  landed first, also `Session` (Decision 9).
- **Depends on:** 032 and 034 (the mount table, its 29 shadows, the trampoline's fuel-neutral
  forward, `MAX_MOUNT_FILES`), 048 (the guard linker: every call has a `_Files` table), 049 (the
  public API frozen: the snapshot, the docstring rules, `defaults()` read once per call), 060
  (the most recent limit with a knob, whose pattern this follows), all landed. 055 (bounded
  sessions) is confirmed for build, revised (`e1ee581` on `spec/055-bounded-sessions`) and not
  landed; Decision 9 says how the two meet. Decision 34 (the snapshot pre-imports no package;
  spec 069, build-class, to follow) moves this limit's cost onto the default path; Decision 2
  says so, for either order.
- **Research it stands on:**
  - `../research/2026-10-18-a-cap-on-open-files.md` (EXECUTED: one host descriptor per file or
    folder a guest opens in a grant and none for a mount; `EIO`, not `EMFILE`, at exhaustion
    today; a prototype counted against caps of 0 to 1,024 and `None`; its fuel delta, exactly 0;
    the fast tier unchanged but for one assertion; each call's peak count in the judge; the
    soft limits a process may set itself; scripts and output beside it), and its addendum after
    the pre-build review;
  - the pre-build review's probes (with the review): `r2_default_vs_soft_limit` (the default
    cap under soft limits of 256 to 2,048), `r8_path_depth` (descriptors held while one path
    call resolves a deep path), `r1_accounting`, `r5_renumber_self_mutant` and
    `r6_unchanged_unit_after_069`;
  - spec 055's pre-build review, F2 (`../reviews/055-bounded-sessions-spec-2026-10-18.md`): one
    call's guest opened 122,870 host descriptors before the host's own `open()` failed;
  - the 0.1.0a2 security review's F11 (`../reviews/0.1.0a2-security-review-2026-10-17.md`):
    while one guest held them, another call's `run` raised `OSError` on the stdlib zip;
  - the owner's answer to question 92 (`../decisions.md`, "The owner's answers of 2026-10-18,
    evening"): a per-sandbox limit on files open at once, set by the embedder like the other
    limits, default 1,024, `EMFILE` past it, for `run` and sessions alike; "the cap guards the
    host process, not what the guest may use"; and Decision 34.

## The problem

A guest can open files in a grant until the embedder's process runs out of descriptors. Each
open file or folder holds one host descriptor (the research, §2). One call's guest opened
122,870, up to the process's own limit on the research's Mac (whose shell had raised its soft
limit to 1,048,576; `kern.maxfilesperproc` is 122,880). Then the host's own `open()` failed with
`EMFILE`: in a door host of that same call, in another call's `run` (which raised on the stdlib
zip), and in the embedder's own code. The guest itself saw `EIO`, because wasmtime maps an OS
error it does not list to `Io`. The README's *Not protected* says so, and that "wasmtime-py
offers no lower limit". A session (spec 055) would hold them for up to an hour.

Constitution §4.15 asks for a default on every limit. Descriptors have none. The owner has
decided there will be one before 0.1.0.

**Where a cap can protect** (the pre-build review's F1). The guest's descriptors share the
embedder's process table, which already holds about eleven before the guest opens anything. So
a cap keeps a guest from starving the process only when the process's soft `RLIMIT_NOFILE` is
above the cap plus what the process holds, for every call and session open at once. The review
ran the default cap of 1,024, with a door host that opens a file after the guest has filled up
(EXECUTED, `r2_default_vs_soft_limit`):

| soft limit | the guest opened, then | the door host's `open()` |
|---|---|---|
| 256 (macOS's default for a process launchd starts) | 245, then `EIO` (29) | `EMFILE` |
| 1,024 (Linux's usual: login shells, systemd services, many container runtimes) | 1,013, then `EIO` | `EMFILE` |
| 1,060 | 1,024, then `EMFILE` (33) | ok |
| 2,048 | 1,024, then `EMFILE` | ok |

So under those two common soft limits the cap alone changes nothing: the process must also
raise its soft limit, or the embedder must set the cap below it. Decisions 5, 7 and 13 say what
this specification does about it.

**What a cap does not count** (the review's F2). wasmtime resolves every guest path through
cap-std. On macOS, and on Linux without `openat2` (kernels before 5.6, or a seccomp profile that
refuses it), cap-std walks a path one folder at a time and holds each parent folder's descriptor
for the length of the call (READ, cap-primitives 4.0.3, `fs/manually/open.rs`). So one path call
holds about one host descriptor per folder in its path, uncounted, while it runs. With a cap of
8 and a writable grant, a guest that made a folder 500 deep and called `os.stat` on its bottom
in a loop held a 512-descriptor process at its limit, and an embedder thread's `open()` failed
476 times (EXECUTED, `r8_path_depth`). That is a limit of this specification, stated
(Decisions 1 and 13); its closer is spec 072, a bound on path depth.

## Decisions

1. **What counts: every file and folder the guest holds open, whatever serves it.**
   - **Counted:** each `path_open` that succeeds, until the guest closes that descriptor or the
     call ends: a file or a folder, in a grant, in the root, in the stdlib's preopen, or in a
     mount.
   - **Not counted:**
     - the three stdio streams and the preopens (the runner makes them before the guest runs,
       from the embedder's arguments; their number is fixed). Closing one frees nothing
       counted; a number wasmtime reuses for a later open is counted from that open;
     - **the descriptors wasmtime holds inside one host call** while it works: a listing's
       directory stream (one), and, for every path call (`path_open` below the cap,
       `path_filestat_get`, `path_create_directory`, `path_unlink_file`, `path_rename` and the
       rest), about one per folder in the path while cap-std resolves it, on macOS and on Linux
       without `openat2` (on Linux 5.6 and later, one). They are gone when the call returns,
       but a guest can make the path as deep as a writable grant lets it, and call again and
       again (the Problem; EXECUTED, `r8_path_depth`). This specification counts what the guest
       holds, not what wasmtime holds for an instant; the README says so (Decision 13), and
       **spec 072, a bound on path depth**, is the closer: a limit on the components of every
       path a path call resolves, so the descriptors one call holds are bounded too.
   - **Mount files count too**, though they hold no host descriptor (the research, §2: 200 mount
     files added 0). The reasons:
     - "Files open at once" then means one thing to the guest, whatever serves a path. Mounts
       are meant to look like files.
     - An embedder who lowers the cap to shrink what one sandbox holds lowers it for mounts as
       well: each open mount file holds a table entry and its staged bytes on the host.
     - Without it, a cap of 1,024 would let a guest hold 1,024 mount files and 1,024 grant files.
     - It costs nothing new: the table already keeps `opened`, the mount's provider numbers in
       use, and `owed`, the numbers the guest has closed whose write-back waits for the ending.
       The cap counts `opened` less `owed`: the guest closed those, and POSIX's close frees the
       descriptor even when the flush fails. (An owed buffer exists only while a call or session
       is stopping, so the difference is seldom seen; `MAX_MOUNT_FILES` keeps counting them.)
   - **This guards the host and limits nothing else.** The guest may open any file its grants
     and mounts allow, as often as it likes, as long as it holds at most the cap at once (the
     owner's principle).

2. **How: the call's `_Files` table counts, through three shadows the guard linker gains.**
   - **No hook exists.** wasmtime-py 49.0.0's `WasiConfig` has no limit on preview1's descriptor
     table, `Store.set_limits` bounds WebAssembly tables, and `RLIMIT_NOFILE` is per process
     (the research, §3). Counting from the host side (`/dev/fd`) is per process, racy between
     calls, and absent on Windows; constitution §4.3 rules that out.
   - **The runner already shadows the right calls.** Every call has a `_Files` table (spec 048).
     A call with mounts runs on the mount linker, which already shadows `path_open`, `fd_close`
     and `fd_renumber`, and forwards a number that is not a mount's to wasmtime's own call
     through the trampoline, fuel-neutral. A call without mounts runs on the guard linker,
     which shadows `fd_readdir` and `path_rename` only. In wasmtime 49's preview1, `path_open`
     is the only call that adds a descriptor the guest keeps (READ, `p1.rs`; confirmed by the
     review).
   - **The change.** A new tuple in `mounts.py`, `COUNTED = ("path_open", "fd_close",
     "fd_renumber")`: the calls that make or free a descriptor the guest holds. The guard linker
     shadows `GUARDED + COUNTED`, in the shared form, as it shadows `GUARDED` today. The table
     serves them with its existing methods, which forward when the number is not a mount's, and
     keeps a set of the wasmtime numbers the guest holds:
     - a forwarded `path_open` that answers 0 adds the number wasmtime wrote at the result
       pointer (read back through `_Memory` after the forward);
     - a forwarded `fd_close` that answers 0 removes its number (if present);
     - a forwarded `fd_renumber(from, to)` that answers 0 with `from != to` removes `to`, then,
       if `from` was held, removes `from` and adds `to`. (wasmtime closes `to` and moves `from`
       there, and answers 0 to `fd_renumber(a, a)` keeping `a`; READ, `p1.rs`, lines 1857 to
       1880.) Without the `from != to` test, `fd_renumber(a, a)` would drop a held `a` from the
       count, and a guest could open without bound (EXECUTED, `r5_renumber_self_mutant`: 50
       opens under a cap of 3).
   - **The count** is the held set's size plus `opened` less the number of `owed` entries
     (Decision 1), as the prototype that made every EXECUTED number counts.
   - **At the call's end** `store.close()` drops every descriptor the guest still holds (as
     today), and the table is released. Nothing carries over to the next call.
   - **One descriptor can go uncounted, for an instant:** a `path_open` whose result pointer is
     out of bounds traps in wasmtime after the open (EXECUTED, the research, §3: the file stays
     held in wasmtime's table). The forward's trap reaches `_shared`, which records the stop and
     sets the epoch deadline to 0, so every later shadowed call answers `EIO` without forwarding;
     the run ends, and the store's close frees it (READ, confirmed by the review). Nothing to
     handle.
   - **Same on every host** (§4.3): it counts preview1 descriptors, not host ones. **No new
     import and no guest change** (§4.4): the shadows define calls the guest already imports.
     `fd_renumber` is not imported by today's binaries (EXECUTED, the research, §2); it is
     shadowed so a later binary is counted exactly, as spec 032 shadowed it for mounts.
   - **What it costs** (EXECUTED, the research, §5; the review re-ran both):
     - **Fuel: nothing.** With a fixed clock and random source, a file-heavy program's fuel was
       the same to the instruction with the shadows off and on, on both binaries, with and
       without a mount (111,512,532 and 331,685,363 without one). The forward sets the guest's
       fuel back. The fast tier and the full judge with a prototype: lost 0, grew 0.
     - **Host CPU: about 50 µs per open-and-close pair** on a call without mounts (92 µs
       against 40 µs on the research's Mac; the review measured 54.5 µs added), the same path a
       call with mounts already takes for every grant call. It is paid once per file opened,
       and the interpreter opens the zip once for each module it imports from it.
     - **Before and after spec 069** (Decision 34). Today the snapshot pre-imports the stack,
       so a typical call on it opens 0 to 3 files: well under a millisecond added. Once 069
       lands, the snapshot imports pandas and the rest from the zip, as the plain reactor does
       today: importing pandas makes 919 opens and closes, about 50 ms of host CPU added, which
       the plain reactor measured as 12 to 15% more host time for `import pandas` (1,147 ms
       against 998 in the research; 964 against 857 in the review), and which is a few percent
       of a pandas script's whole call after 069 (its import costs about 4.63 G fuel). That cost
       is accepted, in either order of landing; the README states it per module, not per
       pre-import (Decision 13), and a cheaper forward is a follow-up on the roadmap (Scope).
     - **Rejected: shadowing `path_open` alone**, and finding closed numbers by asking wasmtime
       about every held number at the cap. It halves the cost per pair, but a guest holding the
       cap and opening in a loop would make the host sweep 1,024 numbers per refused open,
       host CPU that fuel does not see.

3. **The rule and where it is checked: at the cap, an open answers `EMFILE` before anything is
   opened.**
   - **The rule:** a `path_open` is refused when the count is already at or above the cap. So
     exactly the cap's number of opens succeed; the next is refused; a close frees exactly one
     slot.
   - **A number that is not a mount's:** checked first, before the forward. wasmtime opens
     nothing and creates nothing (an `O_CREAT` or `O_TRUNC` open at the cap leaves the folder
     and the file as they were; EXECUTED, `r1_accounting`), so the host never holds more than
     the cap for the guest. `EMFILE` then wins over every other answer the open could have given
     (a missing path, a bad flag), as Linux's `open` allocates the descriptor before it walks
     the path.
   - **A mount's number:** checked where the table already answers `EMFILE` past
     `MAX_MOUNT_FILES`: after the runner's own path answers, before any provider call. So a
     refused open makes no provider call and spends no file call, and spec 032's order of
     answers is unchanged.
   - Below the cap, every answer is the one the call gives today (criterion 1 compares a guard
     table's raw answers with plain wasmtime's).

4. **It fails as a normal OS does: `EMFILE`, and the guest runs on.**
   - The answer is preview1's `EMFILE` (33), the guest's `errno.EMFILE`. Python raises
     `OSError` with that errno; wasi-libc's text is "No file descriptors available" (EXECUTED).
     The guest can close files and continue.
   - **Not a stop.** `max_file_calls` ends a run because a provider call cannot be refused
     without breaking the guest's libc; an open can be refused cleanly, and every libc handles
     `EMFILE`. The run's `exit_code` and `trapped` are the program's own.
   - **An import at the cap fails too:** the zip is opened per module, so a guest that holds the
     cap and imports a module from the zip gets `ImportError` (from `EMFILE`). After spec 069
     that includes pandas and the rest of the stack. A guest imports before it fills the cap,
     and the checks do (criteria 4 and 5).
   - **No record field.** The guest's `OSError` is the signal, in its own output; the embedder
     chose the cap. A count in `Completed` would be one more public name to freeze, as spec 060
     reasoned for its budget. A raw door host that wants it can be told by the guest.
   - **Better than today** even at the host's own limit: today the guest sees `EIO` there
     (EXECUTED, the research, §2), with no sign that closing would help.

5. **The default is 1,024, and the README says where it protects.**
   - **The owner's number.** It equals `MAX_MOUNT_FILES`, the mount table's bound since spec 032.
     A program written within Linux's usual soft limit of 1,024 fits it: there, the 1,024
     include the interpreter's own few descriptors; here the cap counts only what the guest
     opens.
   - **Where it protects** (the Problem's table; the review's F1). The cap is on top of what the
     process already holds, so it keeps a guest from starving the process only where the soft
     `RLIMIT_NOFILE` is above the cap plus the process's own descriptors, times the calls and
     sessions open at once. Under macOS's default of 256 and Linux's usual 1,024, the host still
     runs out first, exactly as today: the guest sees `EIO`, and other code `EMFILE`.
   - **Kept at 1,024** (the lane's ruling on F1). A default below 256 would refuse programs that
     work on every normal OS, and would still not cover several calls at once. Raising the
     process's soft limit from inside the library would change state the embedder's process
     owns, which a library should not do unasked. So: the library never touches process limits;
     the README tells the embedder, in plain words, to raise the soft limit (as the Go runtime
     does for every Go program since 1.19) or to set `max_open_files` below it (Decision 13);
     the command, which owns its process, raises its own (Decision 7). Question 100 asks the
     owner whether the library should raise the limit itself, or the default drop below 256;
     the recommendation is no to both. The build does not wait on it.
   - **No legitimate workload meets it.** The prototype logged every call's peak in the judge's
     fast tier: 1,180 calls, no refusal; 6 or fewer open at once but in two checks built to
     exhaust (the research, §5); the full judge's calls through `run` are the same.
   - **It needs no owner's decision beyond the one given.** It is a new, tighter limit; §4.15
     asks the owner only for a looser default, and the owner chose this one.

6. **The knob: `max_open_files=` on `run` and `run_async`, and `Defaults.open_files`.**
   - **The names** follow the pairs that exist: `max_file_calls=` and `Defaults.file_calls`,
     `max_tool_calls=` and `Defaults.tool_calls`, `max_tool_request_bytes=` and
     `Defaults.tool_request_bytes`.
   - **Its values**, by `_integer_limit`'s rules: an integer from 0 to 2**63 − 1, or `None` for
     no limit. `True` is a `TypeError`; a negative number or 2**63 is a `ValueError` naming
     `max_open_files` (in `Defaults`, `open_files`).
   - **0 refuses every open**, the stdlib zip's included. Today the snapshot still runs what it
     pre-imported; after spec 069 that is the bootstrap only. The plain reactor cannot start (it
     exits 1, "Failed to import encodings module"); a cap of 1 is enough for it, since the zip
     is opened one read at a time (EXECUTED, the research, §4). The `Args:` entry says "0
     refuses every open, the stdlib's included" in one clause.
   - **It applies to every call**, with or without grants, mounts or a root: the stdlib's preopen
     is always there. It needs no other argument, unlike `max_tool_calls`.
   - **Unset, it takes `defaults().open_files`** from the call's one read of the defaults:
     `_check_places` already receives that read (`limits`), so the count of reads per call stays
     one (spec 049, criterion 10).
   - **Placed last.** The keyword goes after `max_tool_request_bytes`, the last keyword of `run`
     and of `run_async`; the field after `tool_request_bytes`, the last field of `Defaults`,
     with its default. Both are what spec 049, Decision 8 lets a minor release add.
   - **Documented** by spec 049, Decision 10's rules: an `Args:` entry in `run` and in
     `run_async`, an `Attributes:` entry in `Defaults`.
   - **The private parts:**
     - `_Files` takes `open_files`, keyword-only, default `None`, after its six existing
       parameters, and keeps it as the attribute `open_files`. The default is `None`, not 1,024,
       so the one source of the default is `defaults()`, and the tables the judge builds by hand
       (`tests/harness/files.py`'s `Mounted` and `Guarded`, one unit in
       `tests/unit/test_runner_mounts.py`) keep no cap. A unit that needs one sets
       `table.open_files` on the harness's table.
     - `_check_places` gains `max_open_files`, keyword-only, default `_UNSET`, after
       `import_path`, and returns it as `"open_files"`; `_checked` passes it by keyword.
     - `_instance` passes `open_files=c["open_files"]`, read strictly as it reads
       `c["file_calls"]` (the review's F7): only `_checked` makes `c`, and a `c` without the key
       (a session that forgot it, say) fails loudly instead of running uncapped.

7. **The command line: `--max-open-files N|none`, and the command raises its own soft limit.**
   - **The flag.** `wasi-python run` takes `--grant`, `--grant-writable` and `--root`, so its
     guests open host files. Without a flag, a command user whose program needs more than 1,024
     files at once would have no way to raise the new default. It parses as `--fuel` does
     (`_limit(int)`: an integer, or `none` for no limit; anything else a usage error, exit 2),
     is listed in `VALUED`, and reaches `run` as `max_open_files` only when given. It is one of
     `run`'s arguments, as spec 019 and spec 049, Decision 7 require of every option. Spec 049,
     Decision 8 lets a minor release add command options; spec 054 added `--import-path` the
     same way.
   - **The command raises its own soft limit to its hard limit at start** (the review's F1, its
     first option, the lane's ruling). The command owns its process, so it may: before it calls
     `run`, where the `resource` module exists (not on Windows), if the soft
     `RLIMIT_NOFILE` is below the hard one, one `resource.setrlimit(RLIMIT_NOFILE, (hard,
     hard))`. A refusal (`ValueError` or `OSError`) leaves the limit as it was, silently, and the
     command goes on. On macOS an unlimited hard limit is accepted (the kernel then holds a
     process at `kern.maxfilesperproc`, 122,880 on the research's Mac; EXECUTED,
     `pj_raise_soft_limit.txt`). Linux's usual hard limit is 4,096 or more, above the cap. So
     the command's default cap guards its own process on both, where the soft limit alone would
     not.
   - **The library never touches process limits.** `run`, `run_async` and everything under
     `wasi_python` but `cli.py` make no `setrlimit` call; the embedder's process is the
     embedder's (Decision 5; criterion 6 checks it).
   - `--max-tool-calls` and the other tool limits stay absent: the command offers no tools.

8. **The guard linker shadows five calls; below the cap a call without mounts still answers as
   wasmtime does; three judge texts change.**
   - The two guards (`fd_readdir`, `path_rename`, spec 048) are temporary: each goes when the
     published floor admits only patched wasmtimes
     (`test_the_rename_and_readdir_guard_match_the_floor`). The three counted shadows are
     permanent. When the guards go, the guard linker keeps `COUNTED`. That rule is unchanged: it
     looks for the advisories' names in `mounts.py`, not at the linker's list.
   - **A guard table's `fd_renumber` forwards whatever the numbers.** Its existing method answers
     `ENOTSUP` for a number in the table or at or above 2**30, to protect provider numbers (spec
     032). A guard table has no mounts and so no provider numbers; there wasmtime's own answer
     (`EBADF` for a number it does not hold) stands. So the rule applies only when the table has
     mounts. No binary imports `fd_renumber` today, but the raw harness reaches it.
   - **Three judge texts change, as a judge change with this reason** (the guard linker now
     shadows five calls, by design; the review's F3 and F6):
     - `tests/unit/test_runner_mounts.py`, `test_a_guard_call_leaves_the_other_calls_native`
       (spec 048, criterion 5): its assertion becomes `sorted(set(seen)) == ["fd_close",
       "fd_readdir", "fd_renumber", "path_open", "path_rename"]`, and its docstring names the
       three counted calls among the shadows instead of listing `path_open` among the calls that
       reach wasmtime directly (EXECUTED: the one failure of the fast tier with the prototype).
       The rest of it (every other call reaches wasmtime without the table; no provider call)
       stands.
     - `tests/unit/test_runner_mounts.py`, `test_a_call_without_mounts_is_unchanged`: its
       assertion `set(served) <= {"fd_readdir", "path_rename"}` becomes `set(served) <=
       set(GUARDED + COUNTED)`, and its docstring ("whose only shadows are fd_readdir and
       path_rename") names the five. Under 068 it passes today only because the snapshot holds
       `json`; once spec 069 lands, `import json` reads the zip and the table serves `path_open`
       and `fd_close` (EXECUTED, `r6_unchanged_unit_after_069`: on the plain reactor, standing in
       for the snapshot after 069, `['fd_close', 'path_open']`). Changing it here means neither
       order of landing meets a red unit.
     - `tests/harness/files.py`, `Guarded`'s docstring ("but for the two calls the guard
       shadows"): it names the five.
     Criterion 1 adds the parity the first no longer covers: below the cap, the three counted
     calls answer as plain wasmtime does.
   - **The code's own texts say the same:** `mounts.py`'s module docstring ("A call without mounts
     shadows only the two calls in `GUARDED`"), the comment above `GUARDED` ("A call without
     mounts shadows these two only"), and `_guard_linker`'s docstring name the counted calls too.
   - The README's sentence "a call without mounts runs on wasmtime's own calls but for the two
     the runner guards" becomes "… but for the two the runner guards and the three it counts
     (`path_open`, `fd_close`, `fd_renumber`), which it forwards to wasmtime".

9. **Sessions (spec 055, not landed): 055's revision already scopes the cap; 068 supplies the
   name.**
   - **What 055's revision says** (`e1ee581` on `spec/055-bounded-sessions`, READ; it supersedes
     the `ddc3fff` text the pre-build review read). Decision 5 carries a bullet, "068's cap on
     open files": per session, set once at the opening and read from `defaults()` then, like
     `memory_bytes`; it counts the descriptors open in the session's store whichever turn opened
     them; it holds through the session's ending, so an `atexit` handler that opens files meets
     it; a turn that meets it gets `EMFILE` and the session goes on. Decision 5's table has a row
     "068's cap on open files | per session". `Session`'s signature takes "the cap on open files
     that 068 adds to `run`, under the name 068 gives it". Decisions 8, 11, 17 and 22 say the cap
     is 068's. Criterion 40, `test_the_cap_on_open_files_in_a_session`, checks it with a cap of
     8, over three turns and the ending's handler; its stand-in is a cap counted per turn. 055
     resets only the table's per-turn counters (`calls`, `faults`, `refused`,
     `refused_total`; its Decision 11), so the held set, `opened` and `owed` carry across turns.
     All of that agrees with this specification.
   - **If 068 lands first** (expected: 055 is build-class and last in its queue): 068 edits no
     055 text but the name. Where 055 says "068's cap on open files" and "under the name 068
     gives it", 055's builder writes `max_open_files=` (in `Session`'s signature, keyword-only,
     after `max_tool_request_bytes`) and `Defaults.open_files`, and builds criterion 40 with
     them. The lane tells 055's branch when 068 lands; if 055's revision is on main by then, 068's
     builder makes that substitution in 055's text on main, a context edit and not a judge
     change.
   - **If 055 has landed first:** 068 carries 055's Decision 5 bullet and its criterion 40 as 055
     wrote them, the ending's handler included (criterion 11 here), and adds the keyword to
     `Session` itself: the signature (keyword-only, after `max_tool_request_bytes`), an `Args:`
     entry, the session's table built with the session's value, one more snapshot line (`param
     max_open_files: int | None = <default>  keyword-only` under `Session`, allowed by the same
     rule as Decision 11's), and the README's *Sessions* table.
   - Either way the session's table is built with `open_files=` from the session's one read of
     the defaults, and `c["open_files"]` (Decision 6) makes a session that forgets it fail
     loudly.

10. **How it meets the other file limits.**
    - **`max_file_calls`** counts provider calls, for mounts only, and ends the run past it. A
      refused open makes no provider call, so it spends no file call. The two limits are
      independent; neither changes.
    - **`MAX_MOUNT_FILES`** (1,024, private) stays as it is: the mount table's own bound on
      provider numbers per call. At the default the two meet at the same count; with a larger
      cap or `None`, it still bounds a mount's files. Folding it into the knob is out of scope.
    - **The staging bound** (`memory_bytes`) bounds mount files' bytes, not their number;
      unchanged.

11. **The snapshot's lines** (spec 049, Decision 13). It adds five lines to
    `tests/public_api.txt` and removes or changes none:

    | line | where | allowed by (049, Decision 8) |
    |---|---|---|
    | `  field open_files: int \| None = 1024` | `dataclass Defaults`, after `tool_request_bytes` | before 0.1.0, any change; after it, a field placed last with a default, and a tighter default |
    | `  param max_open_files: int \| None = <default>  keyword-only` | `def run`, after `max_tool_request_bytes` | a keyword-only argument; its default is a tighter limit (exception 1) and closes the a2 review's F11 (exception 2) |
    | the same line | `async def run_async`, after `max_tool_request_bytes` | the same |
    | `default open_files = 1024` | after `default tool_request_bytes = 16777216` | a tighter default (exception 1) |
    | `  option --max-open-files N  store` | `command wasi-python`, after `--fuel` | a command option (an addition) |

    The command's raise of its own soft limit (Decision 7) is behaviour, not a snapshot line.
    The README's generated reference changes in the entries for `Defaults`, `run`, `run_async`
    and the command's table, by `tests/harness/api.py --write`. The CHANGELOG gains two lines,
    one per exception it relies on: a **Security** line (exception 2) and a **Changed** line
    (exception 1) (Decision 13). The landing uses `--accept-judge`.

12. **Checks first, by counts.** Each new check is seen failing on main (the branch's base,
    `ef1441b` or the lane's later one) before the code changes, and against its named stand-ins
    after. No check measures time: the units count forwards, provider calls, `setrlimit` calls
    and answers; the guest checks count opens, errnos and exit codes. The check that needs more
    than 1,024 host descriptors runs in a child process that sets its own soft limit (criterion
    5), as the existing descriptor checks do, so the judge's own process is never starved and a
    host whose default soft limit is 256 (macOS) runs it too.

13. **The README and the CHANGELOG.**
    - *Running it*, the list of what `run` also takes: `max_open_files` (the files and folders
      a guest holds open at once; see *Safety*).
    - *Mounts*, **Limits**, the "open files" item: "at most `max_open_files` open files and
      folders per call (1,024 by default), counted with those in grants and the root, and at
      most 1,024 in mounts whatever the cap; the next open answers `EMFILE` without calling the
      provider. They cost no host descriptor."
    - *From async code*, "How many run at once": "plus the disk a guest writes and the file
      descriptors it opens" becomes "… and up to `max_open_files` file descriptors each (1,024 by
      default), within the process's own soft limit (see *Safety*)".
    - *Safety*, **defaults**: "1 GiB of memory, a 60 s deadline, 16 MiB of output per stream"
      gains "and 1,024 files open at once (`max_open_files`; past it an open answers `EMFILE` and
      the guest runs on)"; **mounts**: the sentence of Decision 8, and "counting costs no fuel
      and about 50 µs of host CPU per open and close on an arm64 Mac: one open and one close per
      module the interpreter imports from the zip, and per file the program opens".
    - *Safety*, a new item after **defaults**, **The cap needs room in your process's own
      limit**: "a guest's descriptors share your process's table. The cap keeps a guest from
      starving your process only when the process's soft descriptor limit is above the cap plus
      what the process holds, for every call and session open at once. macOS starts a process
      at 256 and many Linux setups at 1,024, where a guest still runs your process out before it
      meets the cap. Raise the soft limit at start (`resource.setrlimit(resource.RLIMIT_NOFILE,
      (hard, hard))` after `soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)`, as the Go
      runtime does for every Go program), or set `max_open_files` below it. The library never
      changes your process's limits; `wasi-python run` raises its own soft limit to its hard
      limit, since it owns its process."
    - *Safety*, **Not protected**, the descriptors item becomes: "the host's file descriptors
      beyond each call's cap: a call or session holds at most `max_open_files` files and folders
      open (1,024 by default), plus its preopens and stdin, and that protects your process only
      within its soft limit (see above); N calls and sessions at once hold up to N times that,
      so size the soft limit for them; with `max_open_files=None` a guest can hold descriptors
      until the process runs out, and then the embedder's own code and other calls' `run` can
      fail with `OSError`, though that guest's own call ends cleanly. The cap counts what the
      guest holds open, not the descriptors wasmtime holds inside one call while it resolves a
      path: on macOS, and on Linux without `openat2`, a path call holds one descriptor per
      folder in the path for as long as it runs, so a guest with a writable grant can build a
      deep folder and bring your process to its limit for the length of its call (a bound on
      path depth is planned)".
    - The API reference and the command's table: regenerated (Decision 11).
    - `CHANGELOG.md`, the 0.1.0a6 section, two lines:
      - a **Security** bullet: "**Security: a cap on files open at once** (spec 068; the 0.1.0a2
        security review's F11 and spec 055's pre-build review's F2; spec 049, Decision 8,
        exception 2). `max_open_files=` on `run` and `run_async`, `Defaults.open_files` and
        `wasi-python run --max-open-files`, default 1,024: the files and folders a guest holds
        open at once, in grants, the root and mounts alike. Past it an open answers `EMFILE`
        before anything is opened, and the guest can close files and go on. Until now a guest
        could open host descriptors until the process's own limit (122,870 on the research's
        Mac), and saw `EIO` there. The cap protects the embedder's process only within that
        process's soft descriptor limit: raise it, or set the cap below it (the README's
        *Safety*); `wasi-python run` raises its own. Descriptors wasmtime holds while it
        resolves a deep path are not counted (*Not protected*). Calls without mounts now pass
        `path_open`, `fd_close` and `fd_renumber` through the runner, which forwards them to
        wasmtime; fuel does not change."
      - a **Changed:** line: "a new, tighter default (spec 068; spec 049, Decision 8, exception
        1): a program that holds more than 1,024 files open at once passes a larger
        `max_open_files`, or `None`."

## Intent

A guest holds at most a set number of files and folders open at once, 1,024 by default, with a
knob the embedder sets like every other limit, on `run`, `run_async`, the command and sessions.
Past it the guest gets `EMFILE`, as on a normal OS, and can close files and go on. Its fuel does
not change, and nothing else it may do with its files changes. Within the process's soft
descriptor limit, which the README tells the embedder to raise and the command raises for
itself, one guest can no longer take by holding files the descriptors the embedder's process
needs. What it holds only for the length of one path call is stated, and spec 072 bounds it.

## Design

```
src/wasi_python/mounts.py     COUNTED = ("path_open", "fd_close", "fd_renumber");
                              _Files(..., engine=None, *, open_files=None): self.open_files, the
                              held set of wasmtime numbers; the count = len(held) + opened −
                              len(owed); _path_open: for a number that is not a mount's, EMFILE
                              at the cap before the forward, the number added after a 0; for a
                              mount, the cap beside MAX_MOUNT_FILES's check; _fd_close: a
                              forwarded 0 removes the number; _fd_renumber: a forwarded 0 with
                              from != to moves or drops, and the ENOTSUP rule only with mounts;
                              the module docstring and GUARDED's comment (Decisions 1, 2, 3, 8)
src/wasi_python/runner.py     Defaults.open_files = 1024 (checked in __post_init__); run and
                              run_async: max_open_files=_UNSET, passed to _checked;
                              _check_places(..., *, import_path=(), max_open_files=_UNSET):
                              read from the same limits, checked by _integer_limit, returned as
                              "open_files"; _instance: _Files(..., open_files=c["open_files"]);
                              _guard_linker: shadows GUARDED + COUNTED, its docstring
                              (Decisions 2, 6, 8)
src/wasi_python/cli.py        --max-open-files N|none, in VALUED, passed when given; before run,
                              the soft RLIMIT_NOFILE raised to the hard one where `resource`
                              exists, a refusal ignored (Decision 7)
tests/unit/test_runner_mounts.py      criteria 1 and 2 (raw, Guarded and Mounted harnesses);
                                      criterion 7 (two units' assertions and docstrings)
tests/harness/files.py                Guarded's docstring (Decision 8)
tests/unit/test_runner_limits.py      criterion 3 (beside the defaults' units)
tests/unit/test_cli.py                criterion 6
tests/checks/test_v1_4_embedding.py   criterion 4 (v1.4: the cap through run and run_async)
tests/checks/test_v1_2_hostile_guest.py   criterion 5 (v1.2: the host keeps its descriptors)
tests/public_api.txt          five lines added (Decision 11), by tests/harness/api.py --write
README.md                     Running it; Mounts' Limits; From async code; Safety (defaults, the
                              cap needs room, mounts, Not protected); the API reference and the
                              command table
CHANGELOG.md                  0.1.0a6: a Security entry and a Changed line
context/specifications/055-bounded-sessions.md   the name only, on main, if 068 lands first and
                              055's revision is on main (Decision 9); otherwise Session in
                              runner.py if 055 lands first
```

In `_path_open`, as a sketch (the builder writes the code):

```
entry = self._entry(fd)
if entry is None:                                   # wasmtime's number
    if self._at_cap():                              # len(held) + opened - len(owed) >= cap
        return EMFILE                               # nothing forwarded, nothing opened
    errno = self.forward(caller, "path_open", args)
    if errno == 0: self.held.add(<the u32 wasmtime wrote at out>)
    return errno
...                                                 # the mount's own answers, unchanged
if self.opened >= MAX_MOUNT_FILES or self._at_cap():   # before the provider
    return EMFILE
```

## Scope

In: Decisions 1 to 13.

Out, each with its reason:
- **The descriptors one path call holds while wasmtime resolves its path** (Decision 1): **spec
  072, a bound on path depth**, not drafted yet. Its intent: a limit on the components of every
  path a path call resolves, so a deep folder cannot make one call hold the process's
  descriptors. Bounding them needs every path call shadowed on calls without mounts, a larger
  change than this one, and its own review. Recorded on the roadmap with question 100.
- **A cheaper forward** for the runner's shadows (about 26 µs per shadowed call today, mounts
  included): a change to the trampoline and `_shared` for every shadow, not to this limit.
  After spec 069 it touches every default call that imports from the zip, so it is recorded
  on the roadmap as a follow-up.
- **Raising the process's soft limit from the library** (Decision 5): question 100.
- **A cap per process**, across calls: the runner keeps no state between calls, and one call's
  cap must not starve another (the reason spec 036 gave for abandoned threads, and spec 060 for
  its budget). The README tells the embedder to size `RLIMIT_NOFILE` for its concurrency.
- **Folding `MAX_MOUNT_FILES` into the knob** (Decision 10): it would change spec 032's bound
  when the knob is `None`; nothing needs it.
- **A count in `Completed` or `stats()`** (Decision 4).
- **Sockets**: preview1 in wasmtime 49 makes none (`sock_accept` answers `ENOTSOCK`), and
  wasmtime-py preopens none.
- **The rest of spec 055's F2**, a session's memory and staging held for its life: 055 states it.

## Acceptance criteria

Each check is written before the code and seen failing on main (the branch's base); each named
stand-in (a mutant of the built code) is applied, its checks run and seen failing, and the file
restored. The landing notes list each with its failing line.

1. **`test_open_files_are_counted_on_a_call_without_mounts`** (unit,
   `tests/unit/test_runner_mounts.py`, no artifacts). `files.Guarded([(tmp_path, "/w", False)])`
   over a folder with five files and one sub-folder; `g.table.open_files = 3`; `g.table.forward`
   wrapped to record each forwarded call's name.
   - Two files and the sub-folder open (raw `path_open` answers 0 three times, three distinct
     numbers); a fourth open answers `EMFILE` (33), and `path_open` was forwarded 3 times, not 4.
   - At the cap, an open of a missing name answers `EMFILE` and is not forwarded.
   - `fd_close` of one held number answers 0; the next open answers 0; the one after, `EMFILE`.
   - Close one; an open of a missing name answers `ENOENT` (forwarded); an open of a file then
     answers 0: a failed open holds nothing.
   - `fd_close` of a number never opened (2**20) answers `EBADF`, and `fd_close(0)` (stdin)
     answers 0; after each, an open still answers `EMFILE`.
   - `fd_renumber(a, b)` of two held numbers answers 0; one open then answers 0, and the next
     `EMFILE`. `fd_renumber(a, 1)` of a held `a` onto stdout answers 0; an open still answers
     `EMFILE`; `fd_close(1)` answers 0; an open then answers 0.
   - **(t)** At the cap, `fd_renumber(a, a)` of a held `a` answers 0, and an open still answers
     `EMFILE`.
   - **(u)** At the cap, `fd_renumber(2, a)` of stderr onto a held `a` answers 0 and frees one:
     the next open answers 0, and the one after `EMFILE`. (stderr, so the earlier rows' closed
     stdin and stdout are not needed; on a fresh harness stdin serves the same.)
   - With `g.table.open_files = None` on a fresh harness, 50 opens answer 0.
   - **Parity below the cap:** with no cap, raw rows of `path_open` (a file, a folder, a missing
     name, a bad descriptor, a bad flag), `fd_close` (held, never opened, stdin) and
     `fd_renumber` (two held numbers; a held number onto itself; `(2**31 - 1, 2**31 - 1)`)
     answer on the `Guarded` harness exactly as on `files.grant_raw` (plain wasmtime): the
     errno, any trap's message, and the number written.

   Seen failing on main: the fourth open answers 0 (no cap; `_Files` has no `open_files` and the
   guard linker forwards nothing for `path_open`). Stand-ins:
   - (a) `>` for `>=`: the fourth open answers 0;
   - (b) the cap checked after the forward (the open undone with a close): `path_open` forwarded
     4 times;
   - (c) `fd_close` frees nothing: the open after the close answers `EMFILE`;
   - (d) every successful close frees one: the open after `fd_close(0)` answers 0;
   - (e) the attempt counted, not the success: the open after the `ENOENT` answers `EMFILE`;
   - (f) `fd_renumber` not tracked: after `fd_renumber(a, 1)` and `fd_close(1)` the open answers
     `EMFILE`;
   - (g) the guard linker without `COUNTED` (main's): the fourth open answers 0;
   - (h) the `ENOTSUP` rule kept in a guard table: the `(2**31 - 1, 2**31 - 1)` renumber row
     answers 58, plain wasmtime 8;
   - (t') the `from != to` test dropped: after (t)'s renumber the open answers 0 (the review's
     `r5_renumber_self_mutant`: 50 opens under a cap of 3);
   - (u') `to` dropped only when `from` is held: after (u)'s renumber the open answers `EMFILE`.
2. **`test_mount_files_count_toward_the_open_file_cap`** (unit,
   `tests/unit/test_runner_mounts.py`, no artifacts). `files.Mounted(MemoryProvider(…),
   placeholder, folders=[(tmp_path, "/w", False)])`; `table.open_files = 4`; the provider's
   calls read from `table.record().calls`.
   - Two mount files and two folder files open (0 each); a fifth open in the folder answers
     `EMFILE` and is not forwarded; a fifth in the mount answers `EMFILE`, and the provider's
     `read` count is unchanged (still 2).
   - Closing a mount file lets a folder file open (0); closing a folder file lets a mount file
     open (0); the next open of either kind answers `EMFILE`.
   - In this table with mounts, `fd_renumber` of two held grant numbers answers 0 and frees one:
     one open then answers 0, and the next `EMFILE` (the build review's F1).
   - A refused open spends no file call: with `file_calls=3` on a fresh harness and the cap at 2,
     two mount opens (2 calls), then two refused mount opens, then `table.total` is 2 and no run
     has ended.

   Seen failing on main: `_Files` keeps no cap (the fifth opens answer 0). Stand-ins: (i) mount
   files not counted (`opened` left out of the count): the fifth mount open answers 0; (j) the
   cap checked after the provider call: the `read` count is 3 for the refused open; (k) the held
   set left out of the count in a mount table: the fifth folder open answers 0; (f2) `fd_renumber`
   left untracked in a table with mounts (the build review's M2): the open after the renumber
   answers `EMFILE`.
3. **`test_the_open_file_cap_is_a_limit_with_a_default`** (unit,
   `tests/unit/test_runner_limits.py`, beside the defaults' existing units, no artifacts;
   artifact lookups counted as spec 053's criterion 1 counts them):
   - `Defaults(1 << 30, 60.0, 16 << 20).open_files == 1024`, and
     `wasi_python.defaults().open_files == 1024`;
   - `Defaults(…, open_files=None)` is accepted; `-1` and `2**63` raise `ValueError`, `True`
     raises `TypeError`, each naming `open_files`;
   - `_checked` unset gives `c["open_files"] == 1024`; `5` gives 5; `None` gives `None`, with no
     grant, mount or root given; `True`, `-1` and `"1"` raise, naming `max_open_files`;
   - `run(["-c", "pass"], max_open_files=-1)` raises `ValueError` with 0 lookups, and so does
     `run_async`'s, with 0 submits;
   - after `set_defaults(replace(defaults(), open_files=7))`, `_checked` gives 7; the old defaults
     are restored in a `finally`.

   Seen failing on main: `Defaults` has no such field. Stand-ins: (l) the field's default `None`;
   (m) `_check_places` reads `open_files` with a second `_current_defaults()` call, which spec
   049's `test_set_defaults_changes_what_run_reads` must fail ("run reads the defaults once").
4. **`test_the_open_file_cap_holds`** (v1.4, `tests/checks/test_v1_4_embedding.py`, through
   `run`, the snapshot). A grant `/w` of 20 files and a mount `/m` of 20 files (a counting
   provider). The guest imports everything it uses (`errno`, `os`) before it opens anything, so
   no import meets the cap (Decision 4). With `max_open_files=8`, the guest:
   - opens grant files until `OSError`, and prints the count and whether `e.errno ==
     errno.EMFILE`: `8 True`;
   - closes one, opens one (it succeeds), and the next open raises `EMFILE`;
   - closes all; opens 4 mount files and 4 grant files; one more mount file and one more grant
     file each raise `EMFILE`; closes one mount file; a grant file then opens;
   - prints what it saw and exits 0.

   The result: `exit_code == 0`, `trapped is None`, the printed line is exact, and
   `done.files.calls["read"] == 4` (the refused mount open made no provider call). With no
   keyword, the same guest's first loop opens all 20 grant files (the default does not meet it).
   **Through `run_async`** (the review's F8), with `max_open_files=2`, a guest that opens grant
   files until `OSError` prints `2 True`.
   Seen failing on main (the keyword is a `TypeError`). Stand-ins: (n) `_instance` passes no cap:
   the first loop opens 20; (o) `EIO` in place of `EMFILE`: `8 False`; (p) the cap refused by
   ending the run, as `max_file_calls` does: `exit_code is None`; (p') `run_async` drops the
   keyword: its guest opens all 20.
5. **`test_a_guest_at_the_open_file_cap_leaves_the_host_descriptors`** (v1.2,
   `tests/checks/test_v1_2_hostile_guest.py`, in a child process, as its neighbour
   `test_a_guest_that_uses_up_host_descriptors_cannot_make_run_raise`). Each guest imports what
   it uses before it opens anything. On a POSIX host the child sets its soft limit to 2,048; if
   its hard limit is below 2,048 the check **skips**, saying "the hard descriptor limit is N,
   below 2,048" (the judge's hosts allow it: EXECUTED here, unlimited). On Windows, which has no
   `RLIMIT_NOFILE` and a per-process handle limit far above these numbers, the child sets
   nothing and runs the same rows (the review's F8). Then:
   - with the defaults, the guest opens a granted file until `OSError`: exactly 1,024 opens, then
     errno 33; it then calls the door, whose host opens and closes a host file: it succeeds; the
     run exits 0;
   - with `max_open_files=None`, the guest opens 1,500 files without error, closes them and exits
     0.

   Seen failing on main: on POSIX the guest opens about 2,030 and gets errno 29 (`EIO`), and the
   door host's `open()` fails with `EMFILE` (as spec 055's review's probe showed at 1,024); on
   Windows the guest opens far past 1,024. Stand-ins: (q) no cap applied: as on main; (r) `None`
   taken as the default: the second guest stops at 1,024.
6. **`test_max_open_files_reaches_run`** and **`test_the_command_raises_its_own_descriptor_limit`**
   (units, `tests/unit/test_cli.py`, the fake `run`):
   - `--max-open-files 5` reaches `run` as `max_open_files=5`; `--max-open-files none` as `None`;
     `--max-open-files=7 x.py` splits off `x.py` as the guest's argv; `--max-open-files x` exits
     2 with nothing on standard output. The existing `test_an_option_not_given_is_not_passed`
     shows it absent when not given.
   - With `resource.getrlimit` and `resource.setrlimit` replaced by recorders: a soft limit of
     256 under a hard one of 4,096 gives exactly one call, `setrlimit(RLIMIT_NOFILE, (4096,
     4096))`, made before `run` is called; a soft limit equal to the hard one gives none; a
     `setrlimit` that raises `ValueError` still gives exit 0 and the result line; with
     `sys.modules["resource"]` set to `None` (as on Windows) the command runs and makes no call.
   - The library makes no such call: no file under `src/wasi_python/` but `cli.py` names
     `setrlimit` (a source rule, as the judge's other source rules read files).

   Seen failing on main: exit 2 (unknown option), and no `setrlimit` call. Stand-ins: (s) the
   option parsed but not passed to `run`; (v) the raise left out: no call; (w) a raise to a fixed
   number (2,048) instead of the hard limit: the call is `(2048, 4096)`; (x) a refused raise
   propagated: exit 1; (y) the raise made in `runner.run` instead of the command: the source rule
   fails.
7. **Three judge texts, changed** (Decision 8):
   `test_a_guard_call_leaves_the_other_calls_native` asserts `sorted(set(seen)) == ["fd_close",
   "fd_readdir", "fd_renumber", "path_open", "path_rename"]`, with its docstring;
   `test_a_call_without_mounts_is_unchanged` asserts `set(served) <= set(GUARDED + COUNTED)`,
   with its docstring; `Guarded`'s docstring names the five. Nothing else in them changes. The
   first is seen failing on main (two names); stand-in (g) fails it. The second, on the plain
   reactor with the prototype, served `['fd_close', 'path_open']` (the review's
   `r6_unchanged_unit_after_069`), which the old assertion refuses and the new one accepts.
8. **Nothing else moves.** The fast tier while building, then the full judge once, in the
   worktree, without `--accept`, against the frozen set `s-4eb5418a2b1bb553-c353b1d9` (or the
   lane's current one): v1.4 gains exactly criterion 4's check and v1.2 criterion 5's; the unit
   suite gains criteria 1, 2, 3 and 6; no pass is lost and nothing grows (the fuel ratchet
   included: the research measured a delta of exactly 0); no existing check meets the default;
   no existing judge file is edited but criterion 7's three texts and `tests/public_api.txt`.
   `test_the_public_api_matches_its_snapshot` passes after `tests/harness/api.py --write`, and
   the snapshot's diff is exactly Decision 11's five lines (six if 055 has landed first);
   `test_every_public_name_is_documented`, `test_the_readme_reference_matches_the_api` and
   `test_set_defaults_changes_what_run_reads` pass. `ruff check` and `ruff format --check` are
   green on `src/` and `tests/`.
9. **Benchmark facts, re-run on the built tree** (recorded in the landing notes, not checks): the
   research's `pe_fuel_exact.py`, adapted to switch the built `COUNTED` off and on, gives a delta
   of 0 on both binaries, with and without a mount; `pf_host_cpu.py` gives the host CPU added
   per open-and-close pair, beside the research's figure; the review's `r8_path_depth`, at one
   fixed depth (300) and the default soft limit, gives the process's peak descriptors during
   the guest's `os.stat` loop, the stated limit spec 072 will close.
10. **The README and the CHANGELOG** carry Decision 13's text; 055's text carries the name if
    Decision 9 asks it.
11. **If 055 has landed first:** 055's criterion 40, `test_the_cap_on_open_files_in_a_session`,
    as 055 wrote it (a cap of 8; turn 1 opens until `EMFILE`; turn 2's open meets `EMFILE`;
    turn 3 closes one and opens one; `ended is None` throughout; a handler at the ending that
    opens files until `EMFILE` lets the ending finish), with `max_open_files=8`; its stand-in, a
    cap counted per turn (turn 2's open succeeds); and one more, the session's table built
    without the keyword (no `EMFILE`).

## Disposition of the pre-build review

The review (in the coordinator's scratchpad, `068-review/`, for the lane to copy to
`../reviews/068-a-cap-on-open-files-spec-2026-10-18.md`, with its probes). Each finding, with the
lane's ruling, and where it went:

1. **F1 (high): at the default, under stock soft limits, the host still runs out first.**
   Written in, the default kept (the lane's ruling). The Problem and Decision 5 carry the fact
   and the review's r2 table; Decision 5 no longer says the default matches Linux's limit as if
   the process held nothing. Decision 13 adds the README's *Safety* item "The cap needs room in
   your process's own limit" (raise the soft limit, as the Go runtime does, or set
   `max_open_files` below it), and *Not protected* says one call needs it too. Decision 7 takes
   the review's first option: the command raises its own soft limit to its hard limit at start,
   one `resource.setrlimit` call, skipped on Windows, a refusal ignored; the library never
   touches process limits. Criterion 6 checks the raise and its absence from the library, with
   stand-ins (v) to (y). Question 100 (`../questions-for-the-owner.md`) asks the owner whether
   the library should raise the limit itself or the default drop below 256, recommending no to
   both; the build does not wait. The Intent says where the cap protects.
2. **F2 (high, macOS and Linux without `openat2`): a path call holds one uncounted descriptor per
   folder in its path.** Written in as a stated limit, not a mechanism (the lane's ruling). The
   Problem states it with r8's numbers; Decision 1's "Not counted" says so and drops the "at
   most one per call in flight" claim; the Scope's entry is now spec 072, a bound on path depth
   (name and intent only; not drafted); Decision 13's *Not protected* and the CHANGELOG say it;
   criterion 9 records r8's peak at a fixed depth. Question 100 carries it to the owner beside
   F1. The roadmap names 072.
3. **F3 (medium): Decision 34 moves the cost onto the default path and breaks a unit.** Written
   in. The branch is rebased onto main `ef1441b` (Decision 34 is `4a94c14`). Decision 2 says what
   changes when spec 069 lands, in either order; Decision 6's cap of 0 says what the snapshot
   keeps after 069; the README's cost text is per module imported from the zip, not per
   pre-import (Decision 13). `test_a_call_without_mounts_is_unchanged` is changed in this judge
   change, its assertion to `set(GUARDED + COUNTED)` and its docstring (Decision 8, criteria 7
   and 8). Criteria 4 and 5's guests import before they fill the cap (Decision 4 says why). The
   cheaper forward is on the roadmap as a follow-up.
4. **F4 (medium): no row renumbers a held number onto itself, and that mutant is an unbounded
   bypass.** Written in: criterion 1's rows (t) and (u), stand-ins (t') and (u'), and the parity
   row for a held number renumbered onto itself. Decision 2 says why `from != to` matters.
5. **F5 (medium): the 055 hand-off was written against an older 055.** Rewritten against 055's
   latest revision, `e1ee581` (the lane's ruling; it supersedes `ddc3fff`). Decision 9: 055
   already scopes the cap per session, through its ending; if 068 lands first, 068 edits no 055
   text but the name (055's builder, or 068's on main if 055's revision is there by then); if 055
   lands first, 068 carries 055's Decision 5 bullet and its criterion 40 as written, ending
   included (criterion 11, which replaces the earlier cap-of-4 unit).
6. **F6 (low): the judge change named one of three texts.** Written in: Decision 8 and criteria 7
   and 8 name all three (two units' assertions and docstrings, `Guarded`'s docstring), and the
   Design names the source texts (`mounts.py`'s module docstring and `GUARDED`'s comment,
   `_guard_linker`'s docstring).
7. **F7 (low): two small choices.** Taken as the lane ruled: `_instance` reads
   `c["open_files"]` strictly (Decision 6); the count is `len(held) + opened − len(owed)`, the
   prototype's (Decisions 1 and 2, the Design).
8. **F8 (low): three criteria gaps.** Written in: criterion 4 has a `run_async` row (a cap of 2)
   with stand-in (p'); criterion 5 runs its rows on Windows without `setrlimit`, and skips with
   its reason where the hard limit is below 2,048.
9. **F9 (note): "122,870 on macOS" was a raised limit.** The Problem and the CHANGELOG now say
   "up to the process's own limit (122,870 on the research's Mac)", beside F1's table.

## Landing notes

Built 2026-10-18 by the implementer (Claude Opus 5.5) in the worktree `../wasi_python-068`, from
`24bc10d` (main `ef1441b` plus this specification). Every claim below was run (EXECUTED) on macOS
arm64, CPython 3.14.2, wasmtime-py 49.0.0, against the frozen artifact set
`build/sets/s-4eb5418a2b1bb553-c353b1d9` of the main tree, read only. Logs are in the worktree's
git-ignored `build/068/`.

### What was built

- `ef0882f`: the code, the checks and the documents, in one commit so that it is green alone (the
  snapshot and the README's reference change with the code).
  - `src/wasi_python/mounts.py`: `COUNTED`; `_Files(..., *, open_files=None)`, the `held` set,
    `open_now()` (`len(held) + opened − len(owed)`) and `_at_cap()`; `_path_open` answers `EMFILE`
    at the cap before the forward (wasmtime's numbers) or beside `MAX_MOUNT_FILES`'s check (a
    mount's), and adds the number wasmtime wrote after a forwarded 0; `_fd_close` and
    `_fd_renumber` keep the set (a renumber onto itself keeps it); the `ENOTSUP` renumber rule
    applies only to a table with mounts; the module docstring and `GUARDED`'s comment.
  - `src/wasi_python/runner.py`: `Defaults.open_files = 1024` (checked, documented);
    `max_open_files=` last on `run` and `run_async` (documented); `_checked` passes it to
    `_check_places`, which reads an unset one from the call's one read of the defaults and returns
    `"open_files"`; `_instance` passes `open_files=c["open_files"]`; `_guard_linker` shadows
    `GUARDED + COUNTED`, its docstring.
  - `src/wasi_python/cli.py`: `--max-open-files N|none`; `_raise_descriptor_limit()` and `OPEN_MAX`
    (Decision 7, with N1).
  - The checks of criteria 1 to 7; the three judge texts of Decision 8; `tests/public_api.txt`'s
    five lines and the README's reference, by `uv run python tests/harness/api.py --write` (its
    diff is exactly Decision 11's five lines); the README's and CHANGELOG's text of Decision 13.

### Seen failing first (criteria 1 to 7)

The new and changed checks against `24bc10d`'s `src/`, before any code changed
(`build/068/seen-failing-main.log`): 9 failed.

```
test_open_files_are_counted_on_a_call_without_mounts   assert (0, 7) == (33, None)   (the 4th open)
test_mount_files_count_toward_the_open_file_cap        the 5th open answers 0
test_a_guard_call_leaves_the_other_calls_native        ['fd_readdir', 'path_rename'] == ['fd_close', …]
test_a_call_without_mounts_is_unchanged                module 'wasi_python.mounts' has no attribute 'COUNTED'
test_the_open_file_cap_is_a_limit_with_a_default       'Defaults' object has no attribute 'open_files'
test_max_open_files_reaches_run                        assert 2 == 0 (unknown option)
test_the_command_raises_its_own_descriptor_limit       [] == [(8, (4096, 4096))]
test_the_open_file_cap_holds                           TypeError: … unexpected keyword argument 'max_open_files'
test_a_guest_at_..._leaves_the_host_descriptors        first row [0, "2036 29 24\n"]: 2,036 opens, then EIO,
                                                       and the door host's open() failed with errno 24
```

### The stand-ins

Each mutant was applied to the built code by `build/068/standins.py`, its checks run, and the file
restored from memory (`build/068/standins.log`); `git diff` of `src/` was the build's afterwards.
Every one was caught.

| stand-in | check | failing line |
|---|---|---|
| (a) `>` for `>=` | criterion 1 | `(0, 7) == (33, None)` |
| (b) the cap checked after the forward | criterion 1 | `4 == 3` (forwards) |
| (c) `fd_close` frees nothing | criterion 1 | the open after the close is `None` |
| (d) every successful close frees one | criterion 1 | `0 == 33` (after closing stdin) |
| (e) the attempt counted | criterion 1 | the open after the `ENOENT` is `None` |
| (f) `fd_renumber` not tracked | criterion 1 | the open after `fd_close(1)` is `None` |
| (g) the guard linker without `COUNTED` | criteria 1 and 7 | `(0, 7) == (33, None)`; `['fd_readdir', 'path_rename'] == [...]` |
| (h) the `ENOTSUP` rule in a guard table | criterion 1 | the parity rows differ |
| (t') the `from != to` test dropped | criterion 1 | `0 == 33` |
| (u') `to` dropped only when `from` is held | criterion 1 | `33 == 0` |
| (f2) `fd_renumber` untracked in a table with mounts (after the build review) | criterion 2 | `33 == 0` |
| (i) mount files not counted | criterion 2 | `(0, 7) == (33, None)` |
| (j) the cap after the provider call | criterion 2 | `3 == 2` (reads) |
| (k) the held set left out in a mount table | criterion 2 | `(0, 7) == (33, None)` |
| (l) the field's default `None` | criterion 3 | `None == 1024` |
| (m) a second read of the defaults | 049's `test_set_defaults_changes_what_run_reads` | "run reads the defaults once" |
| (n) `_instance` passes no cap | criterion 4 | `20 None opened opened opened 8` |
| (o) `EIO` for `EMFILE` | criterion 4 | `8 False 29 29 29 8` |
| (p) the cap ends the run | criterion 4 | `exit_code=None`, `trapped='out of file calls'` |
| (p') `run_async` drops the keyword | criterion 4 | `20 None` |
| (q) no cap applied | criterion 5 | `2036 29 24` |
| (r) `None` taken as the default | criterion 5 | the second guest stops at 1,024 |
| (s) the option not passed | criterion 6 | `KeyError: 'max_open_files'` |
| (v) the raise left out | criterion 6 | `[] == [(8, (4096, 4096))]` |
| (w) a raise to a fixed 2,048 | criterion 6 | `[(8, (2048, 4096))] == [(8, (4096, 4096))]` |
| (x) a refused raise propagated | criterion 6 | `ValueError: not allowed` |
| (y) the raise made in `runner.run` | criterion 6 | `['cli.py', 'runner.py']` |
| (z) no retry at `min(hard, 10240)` (N1) | criterion 6 | the calls lack `(10240, inf)` |

### Criteria 8 to 11

- **Criterion 8, the judge.** The fast tier while building, `uv run pytest -m "not slow" -n 3`, last
  on `ef0882f`'s tree (`build/068/fast-built.log`):

  ```
  wasi_python v1: 353/418 pass · 0 gap · 19 blocked · 0 fail · 46 deselected   (unit suite 1228/1236, 8 skipped)
    v1.2  portable, sealed    66/67  blocked 1
    v1.4  embedding           163/163
  ratchet vs 2ce08a592d: lost 0 · absent 0 · unrun 0 · unrun locally 17 · gained 2 · grew 0 · …
  1581 passed, 27 skipped in 189.10s
  ```

  Against main's fast tier at the research (351/416, v1.2 65/66, v1.4 162/162, unit suite
  1,223/1,231), v1.2 and v1.4 gain exactly criteria 5 and 4, and the unit suite five units
  (criteria 1, 2, 3 and 6's two). The full judge, once, `uv run pytest -n 3`, without `--accept`,
  on `ef0882f` (`build/068/full-built.log`; its record kept as `build/progress/latest.json`, and a
  copy as `build/068/latest-full-ef0882f.json`):

  ```
  wasi_python v1: 365/418 pass · 2 gap · 51 blocked · 0 fail   (unit suite 1228/1236, 8 skipped)
    v1.4  embedding           163/163
  ratchet vs 2ce08a592d: lost 0 · absent 0 · unrun 0 · unrun locally 37 · gained 2 · grew 0 ·
    upstream unrun 31 · judge changed: tests/checks/test_v1_2_hostile_guest.py,
    tests/checks/test_v1_4_embedding.py, tests/harness/files.py and 4 more
  1593 passed, 59 skipped, 2 xfailed in 161.36s
  ```

  The 51 blocked are the worktree's missing source trees and other artifacts, as at the research's
  run; not this change. Nothing grew, so no `--accept-growth`. The judge files changed:
  `tests/checks/test_v1_2_hostile_guest.py`, `tests/checks/test_v1_4_embedding.py`,
  `tests/harness/files.py` (a docstring), `tests/public_api.txt`, `tests/unit/test_cli.py`,
  `tests/unit/test_runner_limits.py`, `tests/unit/test_runner_mounts.py`: new checks, and of the
  existing ones only Decision 8's two assertions and three docstrings. `ruff check` and `ruff format
  --check` are green on `src/` and `tests/`; `tests/harness/api.py --check` exits 0.
- **Criterion 9, benchmark facts** (not checks; this machine had other judges running):
  - fuel, the research's `pe_fuel_exact.py` on the built tree (it switches `mounts.COUNTED` off and
    on, as the prototype's did; `build/068/pe_fuel_exact_built.txt`): delta 0 in all four rows,
    to the instruction (111,512,532; 113,321,812; 331,685,363; 333,493,998);
  - host CPU, `pf_host_cpu.py` (`build/068/pf_host_cpu_built.txt`): open and close 43.3 µs off,
    108.8 µs on, 65.5 µs added per pair (the research 52, the review 54.5); the plain reactor's
    `import pandas` 738 ms off, 830 ms on (+12.5%);
  - path depth, `build/068/path_depth_built.py` (`path_depth_built.txt`; adapted from the review's
    `r8_path_depth.py`): with `max_open_files=8`, a guest that built a folder 300 deep and stat its
    bottom 300 times took this process from 4 descriptors to a peak of 311. That is the stated
    limit (Decision 1) spec 072 will close.
- **Criterion 10.** The README and the CHANGELOG carry Decision 13's text, in the unreleased
  section (the review's N3): "0.1.0a7 — unreleased" since the rebase onto `a0de463` (0.1.0a6 was
  tagged without 068). Decision 9 asks no 055 edit now: 068 is
  landing first, so the lane tells 055's branch the names `max_open_files=` and
  `Defaults.open_files`.
- **Criterion 11** does not apply: 055 has not landed.

### Departures from the specification

- **The command raises its limit only when it is its own process** (Decision 7). The raise is in
  `cli.main()` when it is called with no argument, which is how `wasi-python` (the console script)
  and `python -m wasi_python` call it; `cli.main([...])` with arguments, as the judge's command
  units and any embedder calling it in its own process do, leaves the process's limits alone. So no
  existing unit's fake had to change, and the judge's own process is never raised by the command's
  units. Criterion 6's unit checks both: `main()` raises, `main(["run", …])` does not.
- **N1 taken:** a refused raise is tried once more at `min(hard, 10240)` (macOS's `OPEN_MAX`;
  10,240 when the hard limit is unlimited), only when that differs from the hard limit and is above
  the soft one; criterion 6 has its row and stand-in (z).
- **N2 taken:** criterion 5's guest loop is bounded at 3,000 opens on every system, not only
  Windows, so a regression fails at once with a count.
- **Criterion 5's two rows print separately**, the capped row first, so the check shows the first
  row's numbers even where the second raises (on main, the keyword's `TypeError`).
- **Criterion 4's `run_async` row** reuses the main guest's fill loop and prints the count (`2
  True`).
- **Criterion 1's ENOENT** is the module's existing `ENOENT` (the rules check refuses a name bound
  twice at module level).

### After the build review

The build review (written in the coordinator's scratchpad, `068-buildreview/`, for the lane to copy
to `../reviews/068-a-cap-on-open-files-build-2026-10-18.md`): "lands"; F1 a suggested row, F2 a
note. Both were taken, with the lane's rebase:

- **Rebased** onto main `a0de463` (0.1.0a6 released, the bump to 0.1.0a7). The CHANGELOG's two
  lines moved from the now-released 0.1.0a6 section into "0.1.0a7 — unreleased".
- **F1:** criterion 2 gains the row: in a table with mounts, `fd_renumber` of two held grant
  numbers frees one (one open answers 0, the next `EMFILE`). Its stand-in (f2), the held set's
  update skipped when the table has mounts (the review's M2), fails it: `33 == 0`
  (`build/068/standins-f2.log`, with (v) and (x) re-run after F2).
- **F2:** the unreachable `if resource is None` in `cli._raise_descriptor_limit` is deleted: with
  `sys.modules["resource"] = None`, `import resource` raises `ImportError`, which the line above
  catches. Criterion 6's row for it still passes.
- **The fast tier after these**, `uv run pytest -m "not slow" -n 3` (`build/068/fast-a0de463.log`):
  `wasi_python v1: 353/418 pass · 0 gap · 19 blocked · 0 fail · 46 deselected (unit suite
  1228/1236, 8 skipped)`, v1.4 163/163; `ratchet vs 2ce08a592d: lost 0 · absent 0 · unrun 0 ·
  unrun locally 17 · gained 2 · grew 0`; 1581 passed, 27 skipped. The changed checks by node id: 4
  passed. `ruff check`, `ruff format --check` and `tests/harness/api.py --check` are clean.

### For the lane

- Accept with `--accept-judge "spec 068: a cap on files open at once; new checks (criteria 1 to
  6), spec 048's guard units changed to the five shadows (Decision 8), and tests/public_api.txt's
  five lines"`. No growth.
- After it lands, tell 055's branch the names (Decision 9).

**Landed 2026-10-19** through the lane, after spec 070. The lane rebased the branch onto main
`7307f6f`. Two conflicts: `context/questions-for-the-owner.md` (main already carried question 100,
copied from this branch, so main's file was kept) and `CHANGELOG.md`'s 0.1.0a7 section (both
entries kept). Otherwise the diff equals the reviewed diff at `624cc62` line for line (EXECUTED,
`build/lane-068/delta.txt`: question 100 and the placeholder line only). The pre-build review and
the build review, each with its confirmation (`../reviews/068-a-cap-on-open-files-spec-2026-10-18.md`,
`../reviews/068-a-cap-on-open-files-build-2026-10-18.md`), were committed on the detached HEAD as
`75f03ab`. No build: 068 changes `src/`, the judge and documents only, so main's set
`s-ff5246a2c2f1a52b` stands. The full judge there, serial: `wasi_python v1: 426/442 pass · 14 gap
· 2 blocked · 0 fail (unit suite 1257/1259, 2 skipped)`, `1683 passed, 4 skipped, 14 xfailed in
938.06s`, accepted with `--accept-judge` (criteria 1 to 6, Decision 8's guard units, the API
snapshot's five lines) as `debb56d`, history line 67; nothing grew (EXECUTED,
`build/lane-068-accept.log`). The rules tier passed (40/40, unpiped); main fast-forwarded. Spec
055, building now, takes `max_open_files=` and `Defaults.open_files` as its Decision 5 and
criterion 40 say. Spec 072 (a bound on path depth) and question 100 stay open.

