# Review of 032 — A filesystem provider, read-only mounts (the build; also a security review)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification,
  its pre-build review or its confirmation. I read `AGENTS.md`, the constitution, the threat
  model (`../research/2026-10-16-a-principal-engineers-direction.md` §2), the 0.1.0a3 security
  review's frame, specification 032 with its landing notes, its pre-build review with the
  Disposition, the Confirmation and the author's note, and the diff (`git show c69cb31`). I read
  all of `src/wasi_python/mounts.py`; in `runner.py` the changed parts and the code around them
  (`_check_places`, `_check_mounts`, `_home_folder`, `_instance`, `_fuel_used`, `_drive`,
  `_check_preopens`, `_Call`, `_shared`, `_epoch_answer`, `_linker`, `_mount_linker`,
  `_trampoline_module`); `tests/harness/files.py`; the new checks' names and bodies where a
  finding needed them; wasmtime 49's `p1.rs` (`fd_renumber`, `unused`, `push`, `fd_allocate`,
  `fd_fdstat_set_rights`) and wasmtime-py 49's `trampoline`, `enter_wasm` and `Val.i32`. Each
  claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** commit `c69cb31` on `spec/032-a-filesystem-provider` in the worktree
  `../wasi_python-032`, rebased onto main `8c56437` (spec 030 landed): `mounts.py` (new),
  `runner.py`, `__init__.py`, `tests/harness/files.py` (new), `tests/unit/test_runner_mounts.py`
  (new), `tests/unit/test_runner_grants.py`, `tests/checks/test_v1_2_hostile_guest.py`,
  `tests/checks/test_v1_4_embedding.py`, `README.md`, `CHANGELOG.md`, the specification.
- **Ran (EXECUTED, darwin-arm64, host CPython 3.14.2 from `uv run`, wasmtime-py 49, main's frozen
  set `build/sets/4befe9de64edc783` read only; `scripts/build.sh` not run).** Scripts and outputs
  are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/032-buildreview/`.
  - `uv sync`, then `WASI_PYTHON_ARTIFACTS=… uv run pytest` in the worktree, no flags
    (`judge.log`); `uv run ruff check src tests`; `uv run ruff format --check src tests`.
  - `hostile.py` → `hostile.txt`: four hostile providers through `run()`.
  - `rawprobe.py` → `rawprobe.txt`: guest-side descriptor tricks on the mount linker (the judge's
    own `Mounted` harness) against a read-only grant: `fd_renumber` onto and from the table and
    the high range, every forward on a mount's preopen with the placeholder's times and listing
    compared before and after, `..` from the preopen, renames across a mount folder and stdio or
    a closed number, closing a mount's preopen and reusing its number.
  - `runprobe.py` → `runprobe.txt`: the file-call limit with and without a deadline, fuel and
    `cancel=`; a cancel set in the last allowed provider call; a provider that calls `run()`
    itself; eight concurrent calls with their own mounts (half metered); a provider that blocks
    past the deadline.
  - `listing_cost.py` → `listing_cost.txt`: what a kept listing holds against what the staging
    bound counts for it.
  - `cycle.py`, `cycle2.py`, `cycle3.py` → `cycle*.txt`: whether a call's mount table is freed
    when `run()` returns.
  - `iovprobe.py` → `iovprobe.txt`: a later `iovec` past memory, mount against grant.
  - `readme_example.py` → `readme_example.txt`: the README's *Mounts* example, both binaries.
  - `margin.py` → `margin.txt`: how much of acceptance 6's 0.05 s deadline is left at the
    provider's third call.
  - `mutants.py` → `mutants.txt`: ten one-line mutants, each applied in the worktree with its
    text asserted to occur once, the four test files run, and the file written back. After the
    run `cmp` against copies taken before (`mounts.py.orig`, `runner.py.orig`) was clean and `git
    status` was empty. Scripts that only needed to read the built code ran against a `git
    archive c69cb31 src/wasi_python` copy under the scratch folder (`src/`), first on `sys.path`
    and checked by `__file__`.

## The judge

EXECUTED (`judge.log`):

```
wasi_python v1: 207/218 pass · 0 gap · 11 blocked · 0 fail   (unit suite 624/632, 8 skipped)
  v1.4  embedding           90/90
ratchet vs aac0a98618: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 18 · grew 0 · judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py, tests/harness/files.py and 2 more
================= 831 passed, 19 skipped in 176.85s (0:02:56) ==================
```

The landing notes' 204/215 and 827 passed were on the pre-rebase branch; these are on the rebased
commit, with spec 030's own checks in main. `ruff check`: all checks passed. `ruff format
--check`: 59 files already formatted. `git status` was empty after the run (no progress file
written). The two skips in `test_runner_grants.py` are Windows-only checks that predate 032.

## Findings, most severe first

### F1 — Medium. A provider can still make `run()` raise, or slip an answer past the bad-answer rule

Decision 4 and the Intent say nothing a provider does can make `run` raise, and that an answer
outside the protocol is `EIO` plus a `FileFault`. The README's *Safety* bullet says the same.
The implementer found and fixed one hole of this class (`isinstance()` running a raising
`__class__`). Three more remain. EXECUTED (`hostile.txt`; a guest that stats, lists and opens a
mount's file):

```
[fake Errno int 0 (stat/list/read)] run RAISED AssertionError:
[fake Errno int 2**32+8] exit=0 trapped=None
   stdout: stat OSError 8 | listdir OSError 8 | open OSError 8 | END
   faults: () calls: {'stat': 1, 'list': 1, 'read': 1}
[exception with metaclass __name__] run RAISED ValueError: metaclass name
[exception whose str() is a hostile str subclass] run RAISED ValueError: format
```

1. **An answer that passes `isinstance(answer, Errno)` without being one.** `isinstance` consults
   `__class__` when the type does not match, so an object whose `__class__` property returns
   `Errno` passes. Then `int(answer)` runs the object's own `__int__` (`mounts.py:481`, `:503`,
   `:525`), and `answer == Errno.EISDIR` its own `__eq__` (`:503`). An `__int__` of 0 makes the
   answer a success with no value: `_list` returns `(0, None, 0)`, `_fd_readdir` stores
   `listing = None` and reaches `assert entry.listing is not None` (`:882`). The
   `AssertionError` is caught by `_shared` as the call's stop and `_drive` raises it from `run`.
   An `__int__` of `2**32 + 8` is truncated by wasmtime-py's `Val.i32` (READ, `_value.py:36-43`)
   to 8: the guest gets `EBADF`, which the closed `Errno` set excludes, and no fault is recorded.
2. **`_described` runs provider code outside every boundary.** It is called inside the `except
   Exception` handlers of `_ask`, `_stat`, `_read` and `_list` (`:458`, `:493`, `:511`, `:548`).
   It reads `type(e).__name__`, which a metaclass property can make raise, and formats
   `str(e).strip().splitlines()[0]`, which a `__str__` returning a `str` subclass can turn into
   arbitrary provider objects (`strip`, `splitlines`, `__format__`). Either raise escapes the
   handler, reaches `_shared`, becomes the call's stop, and is raised from `run`.

None of this is reachable by the guest (INFERRED: the guest picks only the path, and a path is a
plain `str`). The provider is the embedder's own code. But the fault boundary is the spec's main
claim about providers, acceptance 7 asserts it, and the fix is small.

**Fix.** Judge every answer by its real type, which never runs provider code: `type(answer) is
Errno` (an enum with members cannot be subclassed, so this is exact), then `int(answer)` is
Errno's own; `issubclass(type(answer), Stat)`; `issubclass(type(answer), (bytes, bytearray,
memoryview))`; and, for tidiness only (it already runs inside the boundary), `type(item) is tuple` in `_listed` (a tuple subclass's `len` and unpacking run
its own `__len__` and `__iter__`). Make `_described` total: its whole body in `try/except
Exception`, the name read with `type.__dict__["__name__"].__get__(type(e))` or replaced by a
fixed text when `type(name) is not str`, and the text kept only when `type(text) is str`, never
formatting a provider object. `_fd_readdir` should treat a listing it could not get as an errno,
not an assertion. Add the three hostile answers above to acceptance 7's table (each `EIO` with one
fault; `run` raises nothing), and see each fail on today's code first.

### F2 — Medium-low. The staging bound counts a listing at about a fifth of what the runner holds

Decision 8 says a listing "is kept as its encoded preview1 entries (24 bytes and the name, each),
so the count is what the runner holds." The code keeps a Python list of `(bytes, int, int)`
tuples (`_list`, `mounts.py:530-546`) and, while gathering, a `set` of every name. EXECUTED
(`listing_cost.txt`, `tracemalloc`, one million 8-byte names):

```
1,000,000 names of 8 bytes: counted 32,000,051 bytes; held 157,434,883 bytes after; peak 239,990,745 while gathering; ratio held/counted 4.9, peak/counted 7.5
```

So under the default `memory_bytes` of 1 GiB, one call's kept listings can hold about 5 GiB of
host memory, and gathering one can peak near 7.5 GiB, while the bound reads 1 GiB. The guest
chooses which folders to open and list (up to 1,024 at once); how large a folder is, is the
provider's namespace. That is the embedder's memory (threat model asset 5), and the README states
the bound as a bound.

**Fix.** Keep each listing as what the count says: one `bytes` of encoded entries (the 24-byte
header with `d_next` written at serve time, or precomputed, then the name) and an `array("I")` of
offsets, so `held` is the bytes held. Judge duplicates without a second structure that the bound
does not count (or count it). A unit check: the bytes a kept listing holds (measured with
`sys.getsizeof` on its parts) are within a small constant of what `held` says.

### F3 — Medium-low. A call's mount table outlives `run()` until the cyclic garbage collector runs

`_Call.__init__` sets `table.call = self` beside `self.table = table` (`runner.py:1903-1905`), a
reference cycle; a forward's error also keeps its traceback in `table.forward_stop`. So the call,
its mount table and every staged file still open when the guest stopped are freed only by the
cyclic collector, not when `run()` returns. A call without mounts has no such cycle. EXECUTED
(`cycle2.txt`, `cycle3b.txt`; a guest that opens a 64 MiB mount file and leaves by `os._exit(0)`):

```
without mounts, live _Call after run(): 0
0 0 b'1\n' b'' live _Call, MiB staged still held: (1, 64)
1 0 b'1\n' b'' live _Call, MiB staged still held: (2, 128)
2 0 b'1\n' b'' live _Call, MiB staged still held: (3, 192)
3 0 b'1\n' b'' live _Call, MiB staged still held: (4, 256)
after gc.collect(): (0, 0)
```

A guest that exits normally closes its files and frees the bytes (EXECUTED, `cycle3.txt`: 0 MiB
held). A guest stopped while holding files does not: out of fuel, a deadline, a cancel, "out of
file calls", a trap, or `os._exit`. Those are exactly the hostile and runaway runs. An embedder
running many calls can hold up to `memory_bytes` per finished call until a full collection
(INFERRED: when that runs depends on the process's allocations).

**Fix.** In `_instance`'s `finally`, after `table.record()`, break the cycle and drop what the
table holds: `call.table = None`, `table.call = None`, `table.table.clear()`, `table.forwards =
None`, `table.forward_stop = None` (once `_fuel_used` has read it). A unit check, by count: after a
`run()` whose guest exits with a mount file open, no `_Call` is alive (`gc.get_objects()` with the
collector disabled) or the provider's returned buffer's `weakref`, through a `bytearray` subclass,
is dead.

### F4 — Low. Three parity differences are in the code but not in Decision 6's table or the README

Decision 6 makes parity with a read-only grant the rule, "except where this table says".

1. **A later `iovec` past memory.** wasmtime reads only the first non-empty `iovec` and does not
   check the others. The runner checks every one (the implementer's choice, Decision 7's "each
   iovec"). EXECUTED (`iovprobe.txt`): two `iovec`s, the second past memory: the grant reads 4
   bytes (`(0, 4, b'hell')`), the mount answers `EFAULT` (21).
2. **An ABI error's `fuel_used`.** A served call that meets an undefined flag or enum value raises
   wiggle's error as the call's stop (the implementer's first choice). `_fuel_used`'s new branch
   restores the count only for a forward's own error (`runner.py:1793-1798`, READ), so a metered
   run ended this way reports `fuel_used is None` on a mount, where a grant reports a count. The
   landing notes name the different `trapped` text; not this.
3. **An absolute path that is not UTF-8** answers `EILSEQ`, where Decision 5's order says `EPERM`
   first. The implementer chose wasmtime's order (decode first), which is right; the spec's list
   should say so.

CPython's own calls never build (1) or (2) (INFERRED: its `readv` buffers are its own memory, and
it passes only defined flags), so this is documentation. **Fix:** a row each in Decision 6's
table and the README's *What differs from a grant*; for (2), either record the fuel at an ABI
error as `forward_stop` does, or state the `None`.

### F5 — Low. No check covers the HOME rule for a mount at `/tmp`

Decision 2: a mount at `/tmp` counts as a read-only grant there, so there is no `HOME`.
`_home_folder` does this in two lines (`runner.py:1643-1644`). Removing them fails no check
(EXECUTED, M9). The rule matters only with a root (`root=True` or a root path) beside a mount at
`/tmp`; without it the runner would make `HOME` in the root's own `tmp`, which the guest cannot
see behind the mount (INFERRED from `_home_folder`). The built code is right: `root=True` with a
mount at `/tmp` gives the guest no `HOME` (EXECUTED, `home.txt`: `HOME = b'None'`, exit 0).
**Fix:** that case as a row in a v1.4 check, seen failing with the two lines removed.

### F6 — Info. Notes that need no change before landing

- **The README's climb rule** says "a climb above the mount, even for a moment, is `EPERM`". The
  code's rule is above the descriptor's own folder (`_resolve`'s `floor`, `mounts.py:600-607`), as
  cap-std's on a grant. `os.open("../x", dir_fd=<a mount folder>)` is `EPERM` even inside the
  mount. Say "above the folder the call starts from".
- **Acceptance 6's 0.05 s deadline** looks wall-clock bound, but the snapshot reaches the
  provider's third call with the whole deadline left (EXECUTED, `margin.txt`: 6 ticks of `stop_at`
  left in 5 of 5 runs on the snapshot, which the check uses; 3 to 4 on the plain reactor). The same
  pattern is already accepted for the door (`test_v1_4_embedding.py:1354`).
- **`_check_mounts`** reads `getattr(provider, method, None)`; a provider property that raises
  anything but `AttributeError` escapes `run()` at check time. That is before any work and is the
  embedder's own object, as with a bad `host`.
- **wasmtime-py internals.** `forward` uses `_ffi.wasmtime_func_call`, `caller._context()`,
  `Func._func`, `Trap._from_ptr` and `WasmtimeError._from_ptr`. The `>=49,<50` pin
  (`pyproject.toml:18`) holds them; the next wasmtime bump must re-run acceptance 12's unit part
  first.

## The implementer's choices where the specification was silent

1. **ABI errors end the run, as on a grant, with wiggle's text.** Agreed. Parity is the rule, and
   ending the run is what a grant does (the grant side of acceptance 3 shows it on every judge,
   EXECUTED in `judge.log`). The error is raised to `_shared`, which records it as the stop
   (READ); 030's guard then keeps every later host function from running. The one gap is the
   `fuel_used` difference (F4.2).
2. **A forward's error keeps today's `fuel_used`.** Agreed. The fuel read before the forward is
   restored in the `finally` before the error is raised (`mounts.py:408-424`, READ). The branch
   applies only when `call.stopped is` that very error and no end is named, so a deadline or a
   cancel surfacing at the trampoline's entry still reports `None`. Removing the branch fails
   `test_forwards_cost_no_fuel_and_keep_traps` (EXECUTED, M4).
3. **UTF-8 decoded when a path is read.** Agreed; wasmtime does the same, and the parity rows show
   it (EXECUTED). Write it into Decision 5 (F4.3).
4. **Every `iovec` checked.** Agreed, as the safer choice; undocumented (F4.1).
5. **A rename or link across a mount and a wasmtime descriptor asks wasmtime by two forwards.**
   Agreed. `fd_fdstat_set_rights` is `get_fd` then `ENOTSUP`, and `fd_allocate` is `get_file_fd`
   then `ENOTSUP` (READ, `p1.rs:1343-1352`, `:1554-1563`): neither changes anything. Renames between
   a mount folder and stdin, stdout, stderr or a closed number answer what a grant answers, 8 in
   all sixteen directions (EXECUTED, `rawprobe.txt`).
6. **A mount's own preopen forwards what wasmtime answers alike for every read-only preopen.**
   Agreed. Every write-shaped forward on it answers what a read-only grant's preopen answers
   (`fd_filestat_set_times` 63, `fd_filestat_set_size` 8, `fd_allocate` 8, `fd_fdstat_set_flags` 8,
   `fd_sync` 8, `fd_write` 8), and the placeholder's times, size and listing were unchanged after
   them (EXECUTED, `rawprobe.txt`: `placeholder unchanged: True []`). Its listing, stat and paths
   are the provider's: `..`, `../ph` and `./../x` from the preopen are 63, as on a grant.
7. **The self-found hole (`__class__` and the iterator's `close`).** The fix is right as far as it
   goes; the same class has three more members (F1).
8. **Acceptance 4's bound of 18.** Agreed: twice the measured 9 on the plain reactor, as the spec
   says; 0 on the snapshot, whose start-up search ran before the snapshot was taken (INFERRED).

## Security, against the threat model

The adversary is the guest: arbitrary Python, every preview1 call the binary imports, the door,
and what the embedder granted (threat model §2). The provider is the embedder's own code and is
not the adversary; it is judged only for robustness (F1). What I tried, and what held:

- **No new import (§4.4).** EXECUTED: both binaries import 42 preview1 calls and `host.call`, as
  before. Of the 42, the 33 that take a descriptor are all in `SHADOWED` or `FORWARD_SAFE`; the
  other nine (`args_*`, `environ_*`, `clock_*`, `proc_exit`, `sched_yield`, `random_get`) take
  none. `test_every_descriptor_import_is_shadowed` checks this per binary, and removing
  `fd_advise` from `SHADOWED` fails it (the landing notes).
- **Guest arguments before any provider call.** READ: `_path`, `_iovecs`, `_result`,
  `_fd_readdir` and `_path_readlink` take every `i32` unsigned and check pointer plus length
  against the memory's size before reading or writing; flags and enums are judged before memory;
  `_resolve` refuses an empty path, a leading `/`, NUL, a component over 255 bytes, a climb above
  the descriptor's folder, and a path under a more specific preopen, before any provider call.
  Memory only grows, so a size read at the start of a call stays valid through the provider call
  (INFERRED; a provider cannot reach the store). Mutants M1 (the length ignored in `fits`) and M5
  (the climb judged against the mount root only) each fail named checks (EXECUTED).
- **Writing to the host through the placeholder.** It is preopened read-only and empty, inside the
  call's `0700` scratch folder, which no grant may reach. Path calls on a mount's preopen are
  served, never forwarded; the forwards that reach it are refused as on a read-only grant and left
  it unchanged (EXECUTED, above). It is checked by identity like every preopen (READ,
  `_check_preopens` runs over `every` on today's linker).
- **`fd_renumber`.** Onto or from the table, and onto or from any number at or above `2**30`,
  answers `ENOTSUP` (EXECUTED: `0→3` 58, provider→4 58, 4→provider 58, `4→2**32-1` 58). A
  renumber below `2**30` onto a number wasmtime does not hold is `EBADF` (EXECUTED: `4→2**30-1`
  8), because wasmtime requires the target to exist (READ, `p1.rs:1867-1868`).
- **`2**30` collisions.** wasmtime's numbers grow only by one above its highest in use or by
  reuse (READ, `p1.rs:434-466`), each costs a live host handle, and a renumber cannot jump. So
  wasmtime reaches `2**30` only with about `2**30` handles open (INFERRED). A provider number not
  open is wasmtime's `EBADF` (EXECUTED: `fd_read(2**30+500)` 8; `fd_prestat_get` on a provider
  number 8).
- **Closing a mount's preopen, then reusing its number.** The table drops it, and the next grant
  open that gets number 3 is served by wasmtime and reads the grant's bytes (EXECUTED).
- **The fault boundary.** Holds against the spec's 25 bad answers and the guard removals the
  landing notes list; fails against the three in F1, none guest-reachable.
- **Forwards.** READ: `wasmtime_func_call` on the caller's context, never `Func.__call__`, so the
  process-wide exception slot is never read; the trampoline's handles and argument arrays are on
  the call's `_Files`; a trap is owned by `Trap._from_ptr`; the fuel is restored in a `finally`.
  The trampoline calls only wasmtime's Rust functions, so no Python callback can fill the slot
  inside a forward, except the runner's own epoch callback, which catches everything (READ,
  `_epoch_answer`).
- **Threads (spec 011).** EXECUTED (`runprobe.txt`): eight concurrent calls, each with its own
  mount and half of them metered, each printed its own file and listing (`True`). The landing
  notes' three-thread check (acceptance 10) passes in `judge.log`.
- **Deadline, cancel, Ctrl-C.** EXECUTED (`runprobe.txt`): a provider that blocks 1.5 s past a
  0.3 s deadline is called once and the run ends `"deadline"`; a cancel set in the last allowed
  call ends `"cancelled"`, not `"out of file calls"`. Mutants M2 and M3 (no cancel or deadline
  check before a provider call) fail `test_a_cancel_or_a_passed_deadline_stops_the_provider_call`
  (EXECUTED). A deferred Ctrl-C waits for a blocked provider, as for a door host; the README says
  so (READ).
- **The limit's naming, with spec 030's order.** EXECUTED: with `max_file_calls=5`, the run ends
  `(None, 'out of file calls', None, b'')` after exactly 5 provider calls with no deadline, with
  fuel, by default, and under `cancel=`. `_epoch_answer`'s new rule (a named end holds) sits after
  the recorded-stop check, as Decision 9 says (READ); see M6 below.
- **Re-entrancy.** EXECUTED: a provider that calls `run()` with its own mount gets its answer, and
  the outer run reads it (`0 None b'hello, mount\n'`).
- **Memory (asset 5).** The open-files bound and the file part of the staging bound hold (the
  judge). The listing part undercounts (F2), and a stopped call's staged bytes outlive `run()`
  (F3).

## Each Decision against the code

1. **The mechanism.** READ and EXECUTED as above: a second linker per engine only for calls with
   mounts, 29 shadows in `_shared`'s form, the forward-safe list, the per-call trampoline bound
   after the guest and before the fuel cap (`_drive`), fuel-neutral forwards, one placeholder per
   call made before the preopens, provider numbers from `2**30`, `fd_close` and `fd_renumber`'s
   rules. Holds.
2. **`Mount` and `mounts=`.** READ (`_check_mounts`) and the judge (19 cases through `run` and
   `run_async`). Holds.
3. **The protocol.** Holds, with F1's gap in how answers are judged.
4. **Faults.** Holds except F1.
5. **Paths.** Holds; the decode order is F4.3.
6. **Parity.** 330 raw rows and 32 guest rows equal on this host (EXECUTED in `judge.log`);
   three undocumented differences (F4). The Linux and Windows answers are unknown until the
   release dry run, as the landing notes say.
7. **Guest memory.** Holds.
8. **Limits.** The call limit and the open-files bound hold (EXECUTED); the staging bound's
   listing part does not count what it holds (F2).
9. **030's invariant.** The comment is worded as the decision says (READ, `runner.py:1975-1988`).
10. **Time, cancel, threads.** Holds (EXECUTED above).
11. **The record.** `Completed.files` is last; `FileRecord.calls` is a read-only mapping with
    zeros; faults keep no exception object (READ). But see F3: the call itself is kept alive by a
    cycle until a collection.
12. **Docs.** The README's example gives the counts it says, on both binaries (EXECUTED,
    `readme_example.txt`). F4 and F6's climb wording are its two gaps.

Decision 2's `HOME` rule holds (EXECUTED, `home.txt`) but has no check (F5).

## Mutants

EXECUTED (`mutants.txt`), the four test files filtered to the mount, file, parity and grant checks:

| mutant | checks failing |
|---|---|
| M1 `_Memory.fits` ignores the length | `test_guest_arguments_never_reach_the_provider`, `test_the_deliberate_differences_are_as_decided` |
| M2 no cancel check before a provider call | `test_a_cancel_or_a_passed_deadline_stops_the_provider_call` |
| M3 no deadline check before a provider call | `test_a_cancel_or_a_passed_deadline_stops_the_provider_call` |
| M4 `_fuel_used`'s forward branch removed | `test_forwards_cost_no_fuel_and_keep_traps` |
| M5 the climb judged against the mount root only | `test_a_path_is_normalized_before_the_provider_sees_it`, `test_raw_calls_answer_as_a_grant_does` |
| M6 `_epoch_answer`'s named-end rule removed | `test_a_named_end_holds_under_the_epoch_callback` |
| M7 the limit sets no epoch deadline | `test_the_file_call_limit_names_the_end` |
| M8 the staging bound off | `test_a_provider_fault_never_escapes[plain, snapshot]`, `test_the_staging_bound_and_the_open_limit` |
| M9 `_home_folder`'s mount-at-`/tmp` rule removed | **none** (F5) |
| M10 a write-shaped open reaches the provider | `test_a_mount_answers_as_a_grant_does[plain, snapshot]`, `test_raw_calls_answer_as_a_grant_does` |

Nine of ten are caught. M2 and M3 are caught only by the unit check, because `_shared` checks the
cancel again after the call; that is enough.

## Acceptance criteria against evidence

1. `test_a_mount_serves_reads` — met (EXECUTED, `judge.log`).
2. `test_a_mount_answers_as_a_grant_does` — met on this host (EXECUTED); other systems at the dry
   run.
3. `test_raw_calls_answer_as_a_grant_does` — met on this host (EXECUTED); other systems at the dry
   run; three differences undocumented (F4).
4. `test_a_mount_at_the_root` — met (EXECUTED); bound 18 agreed.
5. `test_the_file_call_limit_stops_the_run` — met (EXECUTED, and `runprobe.txt` adds the cases
   without a deadline and with fuel).
6. `test_a_mount_keeps_its_deadline_and_cancel` — met (EXECUTED; margin in `margin.txt`).
7. `test_a_provider_fault_never_escapes` — met as written; the guarantee behind it is not (F1).
8. `test_guest_arguments_never_reach_the_provider` and `test_mount_descriptors_are_bounded` —
   met (EXECUTED); M1 fails the first.
9. `test_a_bad_mount_is_refused_before_any_work` — met (EXECUTED).
10. `test_a_call_without_mounts_is_unchanged` — met (EXECUTED; ratchet `grew 0`).
11. `test_the_errno_values_are_the_guests` — met (EXECUTED).
12. `test_forwards_cost_no_fuel_and_keep_traps` — met (EXECUTED); M4 fails it.
13. `test_every_descriptor_import_is_shadowed` — met (EXECUTED; my own import listing agrees).
14. Judge green, lost 0, grew 0, ruff clean — met (EXECUTED). `--accept-judge` and the release dry
    run are the lane's and are not yet run.
15. This review.

## Constitution checks

- §4.4: no import added (EXECUTED). §4.5: no embedder is named in `src/`, `tests/`, `README.md` or
  `CHANGELOG.md` (EXECUTED, `grep` of the diff for `vfs`: none). §4.9: the new checks count calls,
  bytes, fuel and errnos; no new check measures time (EXECUTED, `grep` of the test diff for
  `time.time`, `perf_counter`, `monotonic`, `sleep`: none); acceptance 6 uses ticks by count.
  §4.10: the landing notes label their claims. §4.13: ruff clean; no dependency added
  (`pyproject.toml` untouched). §4.15: every new limit has a default; a call without mounts is
  unchanged; nothing is loosened. Not build-class: no `scripts/`, `recipes/`,
  `downloads/SHA256SUMS` or workflow change.

## Disposition (filled in by the author, then confirmed by the reviewer)

By the implementer, 2026-10-17, in `9c60d91` on `spec/032-a-filesystem-provider` (on the lane's
`c69cb31`). Each fix's check was seen failing first, on the reviewed code swapped in or with its
one rule removed; numbers and the rest are in the specification's landing notes ("Revised …").

1. **F1: fixed.** Every answer is judged by its real type (`type(answer) is Errno`,
   `answer is Errno.EISDIR`, `issubclass(type(…), …)` for `Stat`, the buffer types and
   `Iterable`; a plain tuple of plain str in `_listed`; sizes and times by type). `_described`
   is total: the type's own name through `type.__dict__["__name__"]`, the text only when
   `str(e)` is a plain str. `_fd_readdir` answers `EIO`, never an assertion. Acceptance 7 has the
   four answers from `hostile.py` (two fake `Errno`s, a raising metaclass name, a hostile str
   text); `hostile.py` rerun on `c69cb31`'s code reproduces each of your results, and on the fix
   each is EIO with one fault.
2. **F2: fixed (not restated).** A listing is one `bytearray` of encoded entries plus an
   `array("I")` of offsets, counted as their allocated size; while it is gathered the repeat-
   finding set is counted too. `fd_readdir` serves one slice of it (the 330 parity rows still
   equal). Your measure, rerun: counted 38,816,299, held 38,818,230 (1.00, was 4.9).
   `test_a_listing_is_counted_as_what_it_holds` checks kept within 4 KiB of the count and the
   gathering peak within 1.25 times a bound it passes; it failed on `c69cb31` (640,051 counted,
   3,153,076 held).
3. **F3: fixed.** `_instance` keeps the record, then `table.release()` drops the files, listings,
   handles, fuel record and the link to the call. A trapped call still lingered through
   wasmtime-py's `Trap` traceback (also without mounts: one `_Call` after running out of fuel),
   so `_drive` drops the traceback of a trap or error it has named, and of a reported wasmtime
   stop. `test_a_finished_call_holds_nothing` counts `_Call`, `_Files` and `_Open` with the
   collector off after an exit with a file open, out of fuel and "out of file calls": 0 (4 on
   `c69cb31`).
4. **F4: documented, and (2) closed.** Decision 5 states when UTF-8 is judged; Decision 6's
   table and the README gain the later `iovec` and the ABI error's `trapped` text. An ABI
   error's `fuel_used` now equals the grant's: `_Files` records the fuel when it raises one
   (`stop_fuel`). `test_an_abi_error_keeps_the_grants_fuel`: 11 on both (the mount's was `None`).
5. **F5: fixed.** `test_a_mount_at_tmp_means_no_home` (v1.4), `root=True` and a root path; with
   the two lines removed it fails (`HOME` made behind the mount).
6. **F6:** the README's climb wording corrected; the other notes need no change.

The judge after the revision: `208/219 pass · 0 fail`, `lost 0 · grew 0`, `835 passed, 19
skipped`; ruff clean.

## Verdict

**Not yet.** The mechanism is sound and the guest-side boundary held against everything I tried:
pointers, paths, renumbers, the placeholder, the high range, threads, the limit and its naming. Fix
F1 (judge answers by real type; a total `_described`) and F3 (break the cycle at the end of the
call), and either fix F2 or change Decision 8 and the README to state what the bound counts.
Document F4, and add F5's row. Then it can land without another full review: a confirmation of those fixes, with
their checks seen failing first, is enough.

## One line

The guest cannot get past a mount; but a provider can still make `run()` raise, listings cost
five times what the bound counts, and a stopped call's staged files outlive it.
