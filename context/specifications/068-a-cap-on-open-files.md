# 068 — A cap on files open at once

- **Status:** drafted 2026-10-18; awaiting its pre-build review. It changes neither the guest's
  imports nor its exports, the artifact set nor the build recipe, so §5.6 does not require a
  review before build; the lane asks one because it adds a limit and a public knob, and closes
  a documented hole.
- **Owner:** Clay Gendron
- **Kind:** runner and docs; **parallel-safe**: `src/` and `tests/` only, with `README.md`,
  `CHANGELOG.md` and this specification (and spec 055's text, Decision 9). No build-class file:
  it touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or workflow, and not the guest.
  The counting needs no guest change: it shadows preview1 calls the guest already imports, on
  the host (Decision 2). **It changes the public API** (spec 049, Decision 13): Decision 11
  lists the five snapshot lines it adds and the rule that allows each. A judge change: new
  checks, `tests/public_api.txt` regenerated, and one assertion of spec 048's check changed
  (Decision 8). The code: `src/wasi_python/mounts.py` (`COUNTED`; `_Files.__init__`,
  `_path_open`, `_fd_close`, `_fd_renumber`), `src/wasi_python/runner.py` (`Defaults`, `run`,
  `run_async`, `_checked`, `_check_places`, `_instance`, `_guard_linker`),
  `src/wasi_python/cli.py`. If 055 has landed first, also `Session` (Decision 9).
- **Depends on:** 032 and 034 (the mount table, its 29 shadows, the trampoline's fuel-neutral
  forward, `MAX_MOUNT_FILES`), 048 (the guard linker: every call has a `_Files` table), 049 (the
  public API frozen: the snapshot, the docstring rules, `defaults()` read once per call), 060
  (the most recent limit with a knob, whose pattern this follows), all landed. 055 (bounded
  sessions) is confirmed for build and not landed; Decision 9 says how the two meet.
- **Research it stands on:**
  - `../research/2026-10-18-a-cap-on-open-files.md` (EXECUTED: one host descriptor per file or
    folder a guest opens in a grant and none for a mount; `EIO`, not `EMFILE`, at exhaustion
    today; a prototype counted against caps of 0 to 1,024 and `None`; its fuel delta, exactly 0;
    the fast tier unchanged but for one assertion; each call's peak count in the judge; scripts
    and output beside it);
  - spec 055's pre-build review, F2 (`../reviews/055-bounded-sessions-spec-2026-10-18.md`): one
    call's guest opened 122,870 host descriptors on macOS before the host's own `open()` failed;
  - the 0.1.0a2 security review's F11 (`../reviews/0.1.0a2-security-review-2026-10-17.md`):
    while one guest held them, another call's `run` raised `OSError` on the stdlib zip;
  - the owner's answer to question 92 (`../decisions.md`, "The owner's answers of 2026-10-18,
    evening"): a per-sandbox limit on files open at once, set by the embedder like the other
    limits, default 1,024, `EMFILE` past it, for `run` and sessions alike; "the cap guards the
    host process, not what the guest may use".

## The problem

A guest can open files in a grant until the embedder's process runs out of descriptors. Each
open file or folder holds one host descriptor (the research, §2). One call's guest opened
122,870 on macOS; then the host's own `open()` failed with `EMFILE`, in a door host of that same
call, in another call's `run` (which raised on the stdlib zip), and in the embedder's own code.
The guest itself saw `EIO`, because wasmtime maps an OS error it does not list to `Io`. The
README's *Not protected* says so, and that "wasmtime-py offers no lower limit". A session
(spec 055) would hold them for up to an hour.

Constitution §4.15 asks for a default on every limit. Descriptors have none. The owner has
decided there will be one before 0.1.0.

## Decisions

1. **What counts: every file and folder the guest holds open, whatever serves it.**
   - **Counted:** each `path_open` that succeeds, until the guest closes that descriptor or the
     call ends: a file or a folder, in a grant, in the root, in the stdlib's preopen, or in a
     mount.
   - **Not counted:** the three stdio streams and the preopens (the runner makes them before the
     guest runs, from the embedder's arguments; their number is fixed); a descriptor wasmtime
     opens and drops inside one host call (`fd_readdir`'s directory stream, READ in the
     research, §2). Closing a stdio stream or a preopen frees nothing counted; a number wasmtime
     reuses for a later open is counted from that open.
   - **Mount files count too**, though they hold no host descriptor (the research, §2: 200 mount
     files added 0). The reasons:
     - "Files open at once" then means one thing to the guest, whatever serves a path. Mounts
       are meant to look like files.
     - An embedder who lowers the cap to shrink what one sandbox holds lowers it for mounts as
       well: each open mount file holds a table entry and its staged bytes on the host.
     - Without it, a cap of 1,024 would let a guest hold 1,024 mount files and 1,024 grant files.
     - It costs nothing new: the table already keeps `opened`, the mount's provider numbers in
       use (owed write-backs included, as `MAX_MOUNT_FILES` counts them; an owed buffer exists
       only while a call is stopping, so the difference is never seen).
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
     which shadows `fd_readdir` and `path_rename` only.
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
       there; READ, `p1.rs`, line 1857.)
   - **The count** is the set's size plus the table's `opened`.
   - **At the call's end** `store.close()` drops every descriptor the guest still holds (as
     today), and the table is released. Nothing carries over to the next call.
   - **One descriptor can go uncounted, for an instant:** a `path_open` whose result pointer is
     out of bounds traps in wasmtime after the open (EXECUTED, the research, §3: the file stays
     held in wasmtime's table). That trap ends the run, and the store's close frees it. Nothing
     to handle.
   - **Same on every host** (§4.3): it counts preview1 descriptors, not host ones. **No new
     import and no guest change** (§4.4): the shadows define calls the guest already imports.
     `fd_renumber` is not imported by today's binaries (EXECUTED, the research, §2); it is
     shadowed so a later binary is counted exactly, as spec 032 shadowed it for mounts.
   - **What it costs** (EXECUTED, the research, §5):
     - **Fuel: nothing.** With a fixed clock and random source, a file-heavy program's fuel was
       the same to the instruction with the shadows off and on, on both binaries, with and
       without a mount (111,512,532 and 331,685,363 without one). The forward sets the guest's
       fuel back. The fast tier and the full judge with a prototype: lost 0, grew 0.
     - **Host CPU: about 50 µs per open-and-close pair** on a call without mounts (92 µs
       against 40 µs on the research's Mac), the same path a call with mounts already takes for
       every grant call. A typical call on the snapshot (the default) opens 0 to 3 files: well
       under a millisecond. The plain reactor opens each module it imports from the zip:
       importing pandas there makes 919 pairs, about 15% more host time (1,147 ms against 998).
     - **Rejected: shadowing `path_open` alone**, and finding closed numbers by asking wasmtime
       about every held number at the cap. It halves the cost per pair, but a guest holding the
       cap and opening in a loop would make the host sweep 1,024 numbers per refused open. A
       cheaper forward for every shadow is a separate change (Scope).

3. **The rule and where it is checked: at the cap, an open answers `EMFILE` before anything is
   opened.**
   - **The rule:** a `path_open` is refused when the count is already at or above the cap. So
     exactly the cap's number of opens succeed; the next is refused; a close frees exactly one
     slot.
   - **A number that is not a mount's:** checked first, before the forward. wasmtime opens
     nothing, so the host never holds more than the cap for the guest. `EMFILE` then wins over
     every other answer the open could have given (a missing path, a bad flag), as Linux's
     `open` allocates the descriptor before it walks the path.
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
   - **No record field.** The guest's `OSError` is the signal, in its own output; the embedder
     chose the cap. A count in `Completed` would be one more public name to freeze, as spec 060
     reasoned for its budget. A raw door host that wants it can be told by the guest.
   - **Better than today** even at the host's own limit: today the guest sees `EIO` there
     (EXECUTED, the research, §2), with no sign that closing would help.

5. **The default is 1,024.**
   - The owner's number. It is Linux's usual soft `RLIMIT_NOFILE`, so a program written for a
     normal OS meets the same limit it would meet there. It equals `MAX_MOUNT_FILES`, the mount
     table's bound since spec 032.
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
   - **0 refuses every open**, the stdlib zip's included. The snapshot still runs what it
     pre-imported; the plain reactor cannot start (it exits 1, "Failed to import encodings
     module"); a cap of 1 is enough for it, since the zip is opened one read at a time (EXECUTED,
     the research, §4). The `Args:` entry says so in one clause.
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
   - **The private parts keep every existing call working**, so no judge file is edited to go
     green (AGENTS.md rule 4):
     - `_Files` takes `open_files`, keyword-only, default `None`, after its six existing
       parameters, and keeps it as the attribute `open_files`. The default is `None`, not 1,024,
       so the one source of the default is `defaults()`, and the tables the judge builds by hand
       (`tests/harness/files.py`'s `Mounted` and `Guarded`, one unit in
       `tests/unit/test_runner_mounts.py`) keep no cap. A unit that needs one sets
       `table.open_files` on the harness's table.
     - `_check_places` gains `max_open_files`, keyword-only, default `_UNSET`, after
       `import_path`, and returns it as `"open_files"`; `_checked` passes it by keyword.
     - `_instance` passes `open_files=c.get("open_files")`: a `c` built by hand without the key
       means no cap.

7. **The command line: `--max-open-files N|none`.**
   - `wasi-python run` takes `--grant`, `--grant-writable` and `--root`, so its guests open host
     files. Without a flag, a command user whose program needs more than 1,024 files at once
     would have no way to raise the new default; with it, the command keeps the power it had.
   - It parses as `--fuel` does (`_limit(int)`: an integer, or `none` for no limit; anything
     else a usage error, exit 2), is listed in `VALUED`, and reaches `run` as `max_open_files`
     only when given. It is one of `run`'s arguments, as spec 019 and spec 049, Decision 7
     require of every option.
   - Spec 049, Decision 8 lets a minor release add command options; spec 054 added
     `--import-path` the same way. The command's own process is the host here, so the default
     already guards it; the flag only lets a user loosen or tighten it.
   - `--max-tool-calls` and the other tool limits stay absent: the command offers no tools.

8. **The guard linker shadows five calls; below the cap a call without mounts still answers as
   wasmtime does.**
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
   - **Spec 048's check changes, as a judge change with this reason.** Its unit
     `test_a_guard_call_leaves_the_other_calls_native` asserts that the guard linker shadows
     exactly `fd_readdir` and `path_rename` (EXECUTED: the one failure of the fast tier with the
     prototype). It now asserts the five names, `fd_close`, `fd_readdir`, `fd_renumber`,
     `path_open` and `path_rename`; its docstring names the three counted calls; the rest of it
     (every other call reaches wasmtime without the table; no provider call) stands. Criterion
     1 adds the parity it no longer covers: below the cap, the three counted calls answer as
     plain wasmtime does.
   - The README's sentence "a call without mounts runs on wasmtime's own calls but for the two
     the runner guards" becomes "… but for the two the runner guards and the three it counts
     (`path_open`, `fd_close`, `fd_renumber`), which it forwards to wasmtime".

9. **Sessions (spec 055, not landed): per session, set once; the count is the session's.**
   - A session keeps its store and its `_Files` table across turns (055, Decisions 6, 7 and 11),
     so a file a turn leaves open stays open in the next turn. The count therefore belongs to the
     session: a per-turn allowance would let each turn open the cap again on top of what earlier
     turns hold. `max_open_files` is set once, when the session opens (it reads the defaults
     then); a turn takes no override. 055 resets only the table's per-turn counters (`calls`,
     `faults`, `refused`, `refused_total`); the held set and `opened` are not among them and
     must not become so.
   - **Who carries it.** 055's builder reads 055, not 068, so the keyword reaches `Session` in
     whichever lands second, and 068 makes sure that one knows (as spec 060, Decision 7 did):
     - **If 068 lands first** (most likely: 055 is build-class and last in its queue), 068's
       branch edits 055's specification, a context edit and not a judge change:
       - a bullet in Decision 5's list "The rule for arguments `run` gains": "**068's
         `max_open_files=`** is per session, set once when it opens: each turn's opens count
         against the session's one table, whose held set and `opened` are never reset between
         turns (068, Decision 9).";
       - `max_open_files` in the `memory_bytes` row of Decision 5's table ("per session"), with
         the reason "descriptors live in the store and stay open across turns";
       - `max_open_files=<default>` in `Session`'s signature in Decision 5, after
         `max_tool_request_bytes`, and its snapshot line in Decision 17's list;
       - Decision 11's paragraph "What a session holds on the host" and Decision 22's bullet "A
         cap on open host descriptors per store" rewritten to say the cap exists (068): a session
         holds at most `max_open_files` files open (1,024 by default) for its life, plus its
         preopens and stdin, and the residual is the cap times the sessions and calls open at
         once;
       - in 055's Design, `src/wasi_python/mounts.py`'s line gains "the held set and `opened`
         kept across turns".
     - **If 055 has landed first**, 068's builder adds the keyword to `Session` itself: the
       signature (keyword-only, after `max_tool_request_bytes`), an `Args:` entry, the session's
       table built with the session's value, one more snapshot line (`param max_open_files: int
       | None = <default>  keyword-only` under `Session`, allowed by the same rule as Decision
       11's), the README's *Sessions* table, and criterion 11's unit.
   - Either way, a session without the keyword is bounded by the default, read when it opens.

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

    The README's generated reference changes in the entries for `Defaults`, `run`, `run_async`
    and the command's table, by `tests/harness/api.py --write`. The CHANGELOG gains two lines,
    one per exception it relies on: a **Security** line (exception 2) and a **Changed** line
    (exception 1) (Decision 13). The landing uses `--accept-judge`.

12. **Checks first, by counts.** Each new check is seen failing on main `434a811` before the code
    changes, and against its named stand-ins after. No check measures time: the units count
    forwards, provider calls and answers; the guest checks count opens, errnos and exit codes.
    The check that needs more than 1,024 host descriptors runs in a child process that sets its
    own soft limit (criterion 5), as the existing descriptor checks do, so the judge's own
    process is never starved and a host whose default soft limit is 256 (macOS) runs it too.

13. **The README and the CHANGELOG.**
    - *Running it*, the list of what `run` also takes: `max_open_files` (the files and folders
      a guest holds open at once; see *Safety*).
    - *Mounts*, **Limits**, the "open files" item: "at most `max_open_files` open files and
      folders per call (1,024 by default), counted with those in grants and the root, and at
      most 1,024 in mounts whatever the cap; the next open answers `EMFILE` without calling the
      provider. They cost no host descriptor."
    - *From async code*, "How many run at once": "plus the disk a guest writes and the file
      descriptors it opens" becomes "… and up to `max_open_files` file descriptors each (1,024 by
      default)".
    - *Safety*, **defaults**: "1 GiB of memory, a 60 s deadline, 16 MiB of output per stream"
      gains "and 1,024 files open at once (`max_open_files`; past it an open answers `EMFILE` and
      the guest runs on)"; **mounts**: the sentence of Decision 8, and "counting costs no fuel
      and about 50 µs of host CPU per open and close on an arm64 Mac; the snapshot's typical
      call opens a handful of files, the plain reactor one per module it imports".
    - *Safety*, **Not protected**, the descriptors item becomes: "the host's file descriptors
      beyond each call's cap: a call or session holds at most `max_open_files` files and folders
      open (1,024 by default), plus its preopens and stdin, and one descriptor at a time inside
      a listing; N calls and sessions at once hold up to N times that, from the embedder's one
      process, so set `RLIMIT_NOFILE` above it, or lower the cap, where many run at once; with
      `max_open_files=None` a guest can hold descriptors until the process runs out, and then
      the embedder's own code and other calls' `run` can fail with `OSError`, though that
      guest's own call ends cleanly".
    - The API reference and the command's table: regenerated (Decision 11).
    - `CHANGELOG.md`, the 0.1.0a6 section, two lines:
      - a **Security** bullet: "**Security: a cap on files open at once** (spec 068; the 0.1.0a2
        security review's F11 and spec 055's pre-build review's F2; spec 049, Decision 8,
        exception 2). `max_open_files=` on `run` and `run_async`, `Defaults.open_files` and
        `wasi-python run --max-open-files`, default 1,024: the files and folders a guest holds
        open at once, in grants, the root and mounts alike. Past it an open answers `EMFILE`
        before anything is opened, and the guest can close files and go on. Until now a guest
        could open host descriptors until the embedder's process ran out (122,870 on macOS), and
        saw `EIO` there. Calls without mounts now pass `path_open`, `fd_close` and
        `fd_renumber` through the runner, which forwards them to wasmtime; fuel does not
        change."
      - a **Changed:** line: "a new, tighter default (spec 068; spec 049, Decision 8, exception
        1): a program that holds more than 1,024 files open at once passes a larger
        `max_open_files`, or `None`."

## Intent

A guest holds at most a set number of files and folders open at once, 1,024 by default, with a
knob the embedder sets like every other limit, on `run`, `run_async`, the command and sessions.
Past it the guest gets `EMFILE`, as on a normal OS, and can close files and go on. Its fuel does
not change, and nothing else it may do with its files changes. So one guest can no longer take
the descriptors the embedder's process needs.

## Design

```
src/wasi_python/mounts.py     COUNTED = ("path_open", "fd_close", "fd_renumber");
                              _Files(..., engine=None, *, open_files=None): self.open_files, the
                              held set of wasmtime numbers; the count = len(held) + opened;
                              _path_open: for a number that is not a mount's, EMFILE at the cap
                              before the forward, the number added after a 0; for a mount, the
                              cap beside MAX_MOUNT_FILES's check; _fd_close: a forwarded 0 removes
                              the number; _fd_renumber: a forwarded 0 moves or drops, and the
                              ENOTSUP rule only with mounts (Decisions 2, 3, 8)
src/wasi_python/runner.py     Defaults.open_files = 1024 (checked in __post_init__); run and
                              run_async: max_open_files=_UNSET, passed to _checked;
                              _check_places(..., *, import_path=(), max_open_files=_UNSET):
                              read from the same limits, checked by _integer_limit, returned as
                              "open_files"; _instance: _Files(..., open_files=c.get("open_files"));
                              _guard_linker: shadows GUARDED + COUNTED (Decisions 2, 6, 8)
src/wasi_python/cli.py        --max-open-files N|none, in VALUED, passed when given (Decision 7)
tests/unit/test_runner_mounts.py      criteria 1 and 2 (raw, Guarded and Mounted harnesses);
                                      criterion 7 (spec 048's assertion, five names)
tests/unit/test_runner_limits.py      criterion 3 (beside the defaults' units)
tests/unit/test_cli.py                criterion 6
tests/checks/test_v1_4_embedding.py   criterion 4 (v1.4: the cap through run)
tests/checks/test_v1_2_hostile_guest.py   criterion 5 (v1.2: the host keeps its descriptors)
tests/public_api.txt          five lines added (Decision 11), by tests/harness/api.py --write
README.md                     Running it; Mounts' Limits; From async code; Safety (defaults,
                              mounts, Not protected); the API reference and the command table
CHANGELOG.md                  0.1.0a6: a Security entry and a Changed line
context/specifications/055-bounded-sessions.md   Decision 9's edits, if 068 lands first;
                              otherwise Session in runner.py
```

In `_path_open`, as a sketch (the builder writes the code):

```
entry = self._entry(fd)
if entry is None:                                   # wasmtime's number
    if self.open_files is not None and len(self.held) + self.opened >= self.open_files:
        return EMFILE                               # nothing forwarded, nothing opened
    errno = self.forward(caller, "path_open", args)
    if errno == 0: self.held.add(<the u32 wasmtime wrote at out>)
    return errno
...                                                 # the mount's own answers, unchanged
if self.opened >= MAX_MOUNT_FILES or <at the cap>:  # before the provider
    return EMFILE
```

## Scope

In: Decisions 1 to 13.

Out, each with its reason:
- **A cap per process**, across calls: the runner keeps no state between calls, and one call's
  cap must not starve another (the reason spec 036 gave for abandoned threads, and spec 060 for
  its budget). The README tells the embedder to size `RLIMIT_NOFILE` for its concurrency.
- **Folding `MAX_MOUNT_FILES` into the knob** (Decision 10): it would change spec 032's bound
  when the knob is `None`; nothing needs it.
- **A count in `Completed` or `stats()`** (Decision 4).
- **Descriptors wasmtime opens inside one host call** (`fd_readdir`'s stream): at most one per
  call in flight, gone when the call returns (Decision 1).
- **Sockets**: preview1 in wasmtime 49 makes none (`sock_accept` answers `ENOTSOCK`), and
  wasmtime-py preopens none.
- **The rest of spec 055's F2**, a session's memory and staging held for its life: 055 states it.
- **A cheaper forward** for the runner's shadows (about 26 µs per shadowed call today, mounts
  included): a change to the trampoline and `_shared` for every shadow, not to this limit.

## Acceptance criteria

Each check is written before the code and seen failing on main `434a811`; each named stand-in
(a mutant of the built code) is applied, its checks run and seen failing, and the file restored.
The landing notes list each with its failing line.

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
   - With `g.table.open_files = None` on a fresh harness, 50 opens answer 0.
   - **Parity below the cap:** with no cap, raw rows of `path_open` (a file, a folder, a missing
     name, a bad descriptor, a bad flag), `fd_close` (held, never opened, stdin) and
     `fd_renumber` (two held numbers; `(2**31 - 1, 2**31 - 1)`) answer on the `Guarded` harness
     exactly as on `files.grant_raw` (plain wasmtime): the errno, any trap's message, and the
     number written.

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
     answers 58, plain wasmtime 8.
2. **`test_mount_files_count_toward_the_open_file_cap`** (unit,
   `tests/unit/test_runner_mounts.py`, no artifacts). `files.Mounted(MemoryProvider(…),
   placeholder, folders=[(tmp_path, "/w", False)])`; `table.open_files = 4`; the provider's
   calls read from `table.record().calls`.
   - Two mount files and two folder files open (0 each); a fifth open in the folder answers
     `EMFILE` and is not forwarded; a fifth in the mount answers `EMFILE`, and the provider's
     `read` count is unchanged (still 2).
   - Closing a mount file lets a folder file open (0); closing a folder file lets a mount file
     open (0); the next open of either kind answers `EMFILE`.
   - A refused open spends no file call: with `file_calls=3` on a fresh harness and the cap at 2,
     two mount opens (2 calls), then two refused mount opens, then `table.total` is 2 and no run
     has ended.

   Seen failing on main: `_Files` keeps no cap (the fifth opens answer 0). Stand-ins: (i) mount
   files not counted (`opened` left out of the count): the fifth mount open answers 0; (j) the
   cap checked after the provider call: the `read` count is 3 for the refused open; (k) the held
   set left out of the count in a mount table: the fifth folder open answers 0.
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
   provider). With `max_open_files=8`, the guest:
   - opens grant files until `OSError`, and prints the count and whether `e.errno ==
     errno.EMFILE`: `8 True`;
   - closes one, opens one (it succeeds), and the next open raises `EMFILE`;
   - closes all; opens 4 mount files and 4 grant files; one more mount file and one more grant
     file each raise `EMFILE`; closes one mount file; a grant file then opens;
   - prints what it saw and exits 0.

   The result: `exit_code == 0`, `trapped is None`, the printed line is exact, and
   `done.files.calls["read"] == 4` (the refused mount open made no provider call). With no
   keyword, the same guest's first loop opens all 20 grant files (the default does not meet it).
   Seen failing on main (the keyword is a `TypeError`). Stand-ins: (n) `_instance` passes no cap:
   the first loop opens 20; (o) `EIO` in place of `EMFILE`: `8 False`; (p) the cap refused by
   ending the run, as `max_file_calls` does: `exit_code is None`.
5. **`test_a_guest_at_the_open_file_cap_leaves_the_host_descriptors`** (v1.2,
   `tests/checks/test_v1_2_hostile_guest.py`, in a child process, as its neighbour
   `test_a_guest_that_uses_up_host_descriptors_cannot_make_run_raise`; skipped on Windows,
   which has no `RLIMIT_NOFILE` to set). The child sets its soft limit to 2,048 (its hard limit
   allows it on the judge's hosts; EXECUTED here: unlimited), then:
   - with the defaults, the guest opens a granted file until `OSError`: exactly 1,024 opens, then
     errno 33; it then calls the door, whose host opens and closes a host file: it succeeds; the
     run exits 0;
   - with `max_open_files=None`, the guest opens 1,500 files without error, closes them and exits
     0.

   Seen failing on main: the guest opens about 2,030 and gets errno 29 (`EIO`), and the door
   host's `open()` fails with `EMFILE` (as spec 055's review's probe showed at 1,024). Stand-ins:
   (q) no cap applied: as on main; (r) `None` taken as the default: the second guest stops at
   1,024.
6. **`test_max_open_files_reaches_run`** (unit, `tests/unit/test_cli.py`, the fake `run`):
   `--max-open-files 5` reaches `run` as `max_open_files=5`; `--max-open-files none` as `None`;
   `--max-open-files=7 x.py` splits off `x.py` as the guest's argv;
   `--max-open-files x` exits 2 with nothing on standard output. The existing
   `test_an_option_not_given_is_not_passed` shows it absent when not given. Seen failing on
   main: exit 2 (unknown option). Stand-in: (s) the option parsed but not passed to `run`.
7. **Spec 048's check, changed** (Decision 8): `test_a_guard_call_leaves_the_other_calls_native`
   asserts `sorted(set(seen)) == ["fd_close", "fd_readdir", "fd_renumber", "path_open",
   "path_rename"]`; nothing else in it changes. Seen failing on main (two names). Stand-in (g)
   fails it.
8. **Nothing else moves.** The fast tier while building, then the full judge once, in the
   worktree, without `--accept`, against the frozen set `s-4eb5418a2b1bb553-c353b1d9` (or the
   lane's current one): v1.4 gains exactly criterion 4's check and v1.2 criterion 5's; the unit
   suite gains criteria 1, 2, 3 and 6; no pass is lost and nothing grows (the fuel ratchet
   included: the research measured a delta of exactly 0); no existing check meets the default;
   no existing judge file is edited but criterion 7's assertion and docstring and
   `tests/public_api.txt`. `test_the_public_api_matches_its_snapshot` passes after
   `tests/harness/api.py --write`, and the snapshot's diff is exactly Decision 11's five lines
   (six if 055 has landed first); `test_every_public_name_is_documented`,
   `test_the_readme_reference_matches_the_api` and `test_set_defaults_changes_what_run_reads`
   pass. `ruff check` and `ruff format --check` are green on `src/` and `tests/`.
9. **Benchmark facts, re-run on the built tree** (recorded in the landing notes, not checks): the
   research's `pe_fuel_exact.py`, adapted to switch the built `COUNTED` off and on, gives a delta
   of 0 on both binaries, with and without a mount; `pf_host_cpu.py` gives the host CPU added
   per open-and-close pair, beside the research's figure.
10. **The README and the CHANGELOG** carry Decision 13's text; `055-bounded-sessions.md` carries
    Decision 9's edits if 068 lands first.
11. **If 055 has landed first:** `test_a_sessions_open_files_are_counted_across_turns` (unit or
    v1.4, a session with a grant and `max_open_files=4`): turn 1 opens 3 files and keeps them in
    a global; turn 2 opens one (it succeeds) and the next raises `EMFILE`; turn 2 closes one, and
    turn 3 opens one. Stand-ins: the count reset at each turn (turn 2 opens 4); the session's
    table built without the keyword (no `EMFILE`).

## Landing notes

Not built.
