# 176: The end of a call frees nothing

- **Status:** drafted 2026-10-31, to be reviewed before it is built (the build recipe: `recipes/reactor_main.c`, compiled into both binaries; constitution §5.6). The owner chose it on 2026-10-31, on the condition that it is ready for production (`../decisions.md`, "The end of a call frees nothing"). Amended the same day against its pre-build review, `../reviews/176-the-end-of-a-call-frees-nothing-spec-2026-10-31.md`, every finding taken (its Disposition).
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Kind:** **build-class** and **a judge change** (Decision 7's harness fields and rows). A recipe, no carried patch (§4.1). Not structural: nothing under `src/` changes. `tests/public_api.txt` does not change.
- **Depends on:** landed: 055 (sessions end through `shutdown`), 073 (`run` unfreezes, then finalizes), 157 (a prepared instance's ending), 162 (the session's reserve, the `checkpoint` export). Meets 175 (Decision 8).
- **Research it stands on:** `../research/2026-10-31-a-lighter-exit.md` and its evidence, `../research/2026-10-31-a-lighter-exit/`. **Drafting reads** (READ): the files cited; the pinned CPython 3.15.2's `pylifecycle.c`, `obmalloc.c`, `tracemalloc.c`, `atexitmodule.c`, `memory.rst` and the wasm32 `pyconfig.h:2021, 2028`; wasi-libc's `dlmalloc/src/dlmalloc.c:10-31` and `malloc.c:2211-2241`, in the prior-art clone at `165235b` (the pin is `2e6fb9d8`; the builder confirms the lines there).

Labels: EXECUTED, run and seen; READ, read from a file, cited; INFERRED, reasoned.

## The problem

1. **Teardown** is `Py_FinalizeEx`. It is 57.4 M of a bare snapshot call's 58.5 M, and 43.0 M of a plain call's 323.8 M (EXECUTED, the memo §1).
2. Returning memory to the allocator is 18.5 M of it. The instance is discarded at once, so that work has no effect.
3. Every ending that skips teardown changes something a program can see (the memo §3): buffered bytes, `atexit`, finalizers, temporary files, a sqlite rollback, warnings. Freeing memory is the only part with no effect.

## Decisions

### 1. Teardown runs whole, and frees nothing

`recipes/reactor_main.c` gains `free_nothing_at_teardown()`. `run` calls it just before `Py_FinalizeEx` (`:561`), and `reactor_shutdown` just before its own (`:767`). When `_tracemalloc` is in `sys.modules` and `is_tracing()` is true, it does nothing, since tracemalloc's stop would strand the lists. Otherwise it installs a hook with `PyMem_SetAllocator` on the raw, mem and object domains, each over the allocator `PyMem_GetAllocator` returns. Its `malloc`, `calloc` and `realloc` call that allocator. Its `free` calls it too until the hook is armed (Decision 2); once armed, it skips the free, within Decision 3's budget.

CPython supports a hook that wraps the existing allocator (`memory.rst:561`). In this build all three domains are the C library's `malloc`: without pymalloc or free threading, `obmalloc.c:440-443` chooses `MALLOC_ALLOC` for each; mimalloc is compiled in but unused, and the isolated configuration (`reactor_main.c:292`) ignores `PYTHONMALLOC`. So `PyObject_Malloc`, `PyMem_Malloc` and `PyMem_RawMalloc` all pass through the hook.

Every finalizer still runs, in CPython's order. A prepared instance (`end_prepared`, `:778`) is unchanged.

### 2. Frees stop only once Python is finalizing

The hook's `free` arms on its first call that finds `Py_IsFinalizing()` true. CPython sets that only after `make_pre_finalization_calls` returns (`pylifecycle.c:2418-2419`): every `atexit` handler has run, those registered during `atexit` included (the loop runs until none is left), and the pending calls with them. The program's last line ran before. So `atexit` handlers free as today. Until it arms, the hook costs one call and one load per free. `Py_IsFinalizing` reads the runtime's state and needs no attached thread state, so the raw domain's `free` may call it.

### 3. A budget over every allocation, and never a trap

Each skipped block goes onto its domain's list, threaded through its first word, where dlmalloc's `free` writes its own link.

**Every allocation is counted.** The link wraps the C library's allocators, as it already wraps others (`60_link.sh:170`): `malloc`, `calloc`, `realloc`, `aligned_alloc`, `posix_memalign`, and musl's internal aliases `__libc_malloc` and `__libc_calloc` (locale and time-zone code calls these; `dlmalloc.c:96-99`). Each `__wrap_` function lives in `reactor_main.c`. Unarmed, it checks one flag and calls the real one. Armed, it adds the **chunk** each request takes, `max(16, (n + 4 + 15) & ~15)` for a request of n bytes (dlmalloc's 4-byte header, 16-byte alignment and 16-byte least chunk, `malloc.c:2211-2241`), plus the alignment for `aligned_alloc` and `posix_memalign`; n is `calloc`'s product, saturating, and `realloc`'s new size, so a shrink counts too. These over-count, which is safe. Python's domains, numpy's data, sqlite, OpenBLAS's emulated `mmap` (`60_link.sh:90-91`), `host_alloc` and `operator new` all reach them.

**The budget.** Before an allocation that would take the count past B, the hook frees every block on the three lists and stops skipping for the rest of the call. An allocation that gets `NULL` while armed does the same, then tries once more; a failed `realloc` leaves its block valid, so its retry is sound. B is 1 MiB.

**The bound.** At any moment of teardown, the heap's chunks take at most B more bytes than today's teardown at the same moment, for every allocator, fragmentation aside (INFERRED). A skipped free costs only memory a later allocation would have reused, and every later allocation is counted. Once the lists are freed, the heap is today's. So no teardown grows toward the cap, with a limit or without.

**What could escape.** Memory taken without `malloc`, or an allocator called past its wrap. A row of the new check file reads both binaries: the only direct callers of the five real allocators are their `__wrap_`s, none of the five is in the function table, and dlmalloc alone calls `sbrk` and `memory.grow` (mimalloc is compiled in, never selected). Anything else is named here, with its residue, a row and a line in `docs/reference/limitations.md`.

**Every block holds a link.** A dlmalloc chunk on `wasm32` is at least 16 bytes with 4 of overhead (`malloc.c:2211-2241`), so 12 bytes are usable and a 4-byte pointer fits. Zero-size requests ask `malloc(1)` (`obmalloc.c:58-95`), and dlmalloc's `malloc(0)` returns a minimum chunk. `free(NULL)` passes through. A skipped block is never handed back, so nothing aliases. A double free traps at the drain where native traps at the second free.

**The size, measured.** This design's hook, counting bytes asked, in the pinned native CPython 3.15.2 (EXECUTED, `tally/`, `out-native-tally.tsv`): teardown asked at most 51,211 bytes in 837 requests in nine programs, from a bare one to a 2,000,000-key dict and a sqlite rollback; in chunks, under 70 KB (INFERRED: 16 bytes more each at most). B is 15 times that. Skipping and draining, each ended the same; 1 MiB churned 500 times passed B and drained. On the memo's spike, teardown grew linear memory by at most 64 KiB in eight cases, numpy and pandas included (`mem.py`, `out-memory.tsv`). The build counts the bytes asked in the guest, numpy and pandas included, with an unshipped counting copy; if any is over 256 KiB, B becomes four times the largest, at most 8 MiB, written here first.

**The state:** three saved allocators, three list heads, the count, and a phase (waiting, armed, done) that never leaves done.

### 4. No instance runs after its teardown

The hook stays installed after `Py_FinalizeEx`. tracemalloc started during teardown wraps it and, stopping, puts it back (`tracemalloc.c:910-925`). That is safe only if nothing runs in the instance afterwards. Nothing does, and this specification forbids it.

The guest (READ, `reactor_main.c`):

- After `run` (`run_called`, `:516`), `run` (`:511`), `turn` (`:626`), `turn_input` (`:726`), `prepare` (`:806`) and `checkpoint` (`:868`) refuse; `shutdown` refuses as no turn ran (`:749`).
- After `shutdown` (`shut`, `:752`), every export refuses on `shut`, and `run` on `turned`.
- Each refusal runs no Python. A refused turn frees its buffer with the C library's `free`, which is never skipped.

The host (READ):

- `_call._call_deferred` closes the store on every path (`_call.py:293-298`, `:546-549`); `_release_session` closes a session's (`_sessions.py:637-660`).
- `checkpoint` reads memory only after a turn returned (`reactor_main.c:868`); a making, after `prepare` (`_sessions.py:954-956`), which never finalizes. `stats()` (`runner.py:859`) reads counters, never an instance.
- A trap during teardown discards the store. Another embedder calling `run` again gets 70 before any Python runs.

The reactor's header gains the rule: after `run` or `shutdown` finalized, every export refuses and the host discards the instance. A later export that runs code after teardown must restore the saved allocators first.

### 5. Threads are moot

CPython asks allocators to be thread-safe (`memory.rst:564-565`). The guest imports no `thread-spawn` (EXECUTED by the review) and its memory is not shared, so `pthread_create` fails and one thread runs. wasip1 delivers no asynchronous signal (`HAVE_SIGACTION`, `HAVE_ALARM`, `HAVE_SETITIMER` undefined); a deadline traps and discards the store. So plain `static`s suffice. A threaded target would need atomics; none is in scope.

### 6. What it does not skip

Frees outside the three domains, such as numpy's data handler's `free`, run as today. So it saves less after numpy than the memo's stub, which stubbed `free` too.

### 7. The judge

The harness (`tests/harness/guest.py`): `Result` and `Turns` gain `memory_size`, the memory's `data_len` after the export returns, and `memory_limit=`, through `store.set_limits`.

A new file, `tests/checks/test_v1_4_the_end_of_a_call.py`, with its cap in `tests/lint/budget.toml` (twice its largest fuel measured at its first build), holds the rows of the acceptance criteria. **Teardown's growth** in a row is `memory_size` less the same program's ending in `os._exit(0)` after a flush. **Teardown's fuel** is fuel less that same program's.

Each probe row's expected outcome is native CPython's, from the memo's `out-matrix.tsv`, written into the file.

### 8. The neighbours

- **175** keeps the stdlib zip's dict alive past teardown. Its 17.6 M is partly frees this hook skips, so what is left to save after it is unmeasured. If 175 lands first, criterion 6's bounds become its base's figure less 8 M (INFERRED); the second to land measures both, and a saving under 8 M restates the bound in the landing notes, as a claimed judge change.
- **162**'s `reserve` (`reactor_main.c:258-274`) is freed by the C library's `free`, never skipped.
- **069**'s check (b), `START_FACTOR` (`test_v1_3_data_stack.py:180`), holds: the ratio rises from about 5.5 to about 7.7 (INFERRED, the memo §4).

### 9. No ending that skips teardown

The memo's opt-in ending, about 57 M a bare call, is not offered (`../decisions.md`): agents write the code this project runs, and agents forget `close()`, so it would turn that into silent data loss. The owner left this to the project ("do what is best for the project and what makes this production ready", 2026-10-31), and the orchestrating session dropped the opt-in.

## Intent

A call ends as CPython ends, every finalizer in its place, without returning memory to an instance that is about to be discarded.

## Design

- **Recipe:** `recipes/reactor_main.c`: `free_nothing_at_teardown()`, its hook, lists, budget and the seven `__wrap_` functions (about 110 lines), the two calls, the header's rule (Decision 4); `scripts/steps/60_link.sh`'s `WRAP` gains the seven.
- **Judge:** `tests/harness/guest.py`; the new check file; `tests/lint/budget.toml`.
- **Documents:** `docs/explanation/fuel.md:33` and `docs/explanation/performance-and-size.md:30`, restated with the measured figures.
- **Bytes:** both binaries grow by the hook, under 1 KB (INFERRED); `MANIFEST` and `SHA256SUMS` change; the news file claims it.

## Scope

In: Decisions 1 to 8. Out: an ending that skips teardown (Decision 9); a prepared instance's ending; skipping frees outside the three domains; threads.

## Acceptance criteria

Criteria 1 to 4 are the owner's four proofs of production readiness. The build does not land unless each holds.

1. **(a) No instance runs after its teardown.** Rows on both binaries: after `run`, and after a session's `shutdown`, each export refuses in under 10,000 fuel. The reviewer READs Decision 4's host paths. EXECUTED and READ.
2. **(b) Teardown's memory, against the cap.** Rows on both binaries, each ending as native does, none trapping. **Room** is what a program leaves after filling the heap under `memory_limit` 64 MiB and dropping part.
   - Teardown's growth is at most 256 KiB after a bare call, `import numpy`, a 200,000-row pandas groupby, 200,000 objects with `__del__` and 200,000 cycles; and after a session's `shutdown` whose turns hold a 500,000-key dict and 50,000 objects with `__del__`.
   - Room 0: the program ends with its lines and exit 0.
   - A `NULL` before the budget: room 512 KiB; a finalizer makes and drops 64 KiB a hundred times, then writes a line with `os.write`. No "Exception ignored".
   - Allocators outside the domains: room 1 MiB; `__main__` holds a 10 MiB `bytes` and, defined after it, an object whose `__del__` makes a 4 MiB numpy array. The hook skips the `bytes`; numpy's `malloc` would pass B, so the drain comes first. It writes its line.
   - C++ `new`: room 2 MiB; a finalizer makes `matplotlib.backends.backend_agg.RendererAgg(256, 256, 72)`, whose constructor takes its pixel buffer with `new[]` (`src/_backend_agg.cpp`), and writes its line. With 128 KiB of room, a second row records what a failed `new` does: this finalizer runs first, with the list empty, so the retry fails as native's would. libc++ is the exceptions build (`60_link.sh:214-216`), so `bad_alloc` is thrown, expected to reach Python as `MemoryError`; the row asserts no trap and records the outcome.
   - A sqlite rollback: room 2 MiB; an uncommitted insert of 1,000 rows in a file the host then reads holds only the committed rows.
   - No limit: a finalizer makes and drops 1 MiB 500 times. Teardown's growth is at most B plus 1 MiB plus 64 KiB, where never draining would grow 500 MiB. EXECUTED.
3. **(c) The hook arms only after `atexit`.** Rows: an `atexit` handler that makes and drops 1 MiB a hundred times grows memory as today (within 64 KiB); a handler registered during `atexit` that does the same, too. The reviewer READs Decision 2 in the pinned CPython. EXECUTED and READ.
4. **(d) Threads.** The reviewer READs Decision 5 against the set: no `thread-spawn` import, memory not shared. READ and EXECUTED.
5. **The probes, rows on both binaries**, each equal to native: P01 to P06, P09 to P19, P25, P29 to P33, P37, P39 and P44 (the memo §2), `sess.py`'s session, and two tracemalloc probes: `tracemalloc.start()` in the program, and `tracemalloc.stop()` in an `atexit` handler. Each is seen failing first against an ending in `os._exit` after a flush. EXECUTED.
6. **The cost, as counts**, each seen failing first on today's set: a bare snapshot call's teardown at most 45 M (57.4 M today), a bare plain call's at most 35 M (43.0 M today). The landing notes record both, and a pandas groupby's teardown. **The wrapper's cost**, a counted fact: recorded fuel rows for a bare call and a pandas groupby on both binaries, each ending in `os._exit(0)` so no teardown is in them; their growth over the base, the unarmed wrapper's, is listed under `GROWTH` with the news file's reason, at most 0.5% (INFERRED). Above 0.5% the figure is recorded and claimed, and the build lands only if the whole call, teardown included, uses less fuel than today for a bare call and a pandas groupby on both binaries. EXECUTED.
7. **The run.** The fast tier, the lint and `ci-status` green; no accepted pass lost; the bytes claimed; the landing notes cite both reviews. READ.

The news file's CHANGELOG line, its number measured:

- Changed: `` - **A call ends on less fuel.** Python still finalizes everything as CPython does, but no longer returns memory to an instance that is about to be discarded: a bare snapshot call costs <measured> instructions, down from 58.5 million. [Fuel](https://claygendron.github.io/wasi-python/explanation/fuel/) ``

## Landing notes

To be written at the landing.
