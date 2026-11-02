# 176: The end of a call frees nothing

- **Status:** built 2026-10-31 with 175 on `spec/175-176-the-zip-directory-and-the-end-of-a-call` (Landing notes), its pull request in review. Drafted 2026-10-31, to be reviewed before it is built (the build recipe: `recipes/reactor_main.c`, compiled into both binaries; constitution §5.6). The owner chose it on 2026-10-31, on the condition that it is ready for production (`../decisions.md`, "The end of a call frees nothing"). Amended the same day against its pre-build review, `../reviews/176-the-end-of-a-call-frees-nothing-spec-2026-10-31.md`, every finding taken (its Disposition).
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

Built 2026-10-31 by an agent (Claude Opus 5.5), a builder sub-agent of the orchestrating session, together with 175 on `spec/175-176-the-zip-directory-and-the-end-of-a-call` from `dev` at `2ec3c1ee`, then rebased onto `a0b1171d`. Its pre-build review, three reads, is `../reviews/176-the-end-of-a-call-frees-nothing-spec-2026-10-31.md`; 175's is `../reviews/175-the-zips-directory-is-read-by-folder-spec-2026-10-31.md`; the pull request's review is to come. 175 was built and measured first, then this specification on top (175's landing notes give the three sets). Everything below is EXECUTED on an arm64 Mac (Darwin 25.5.0), through the judge's driver, unless labelled.

**Criterion 6, teardown.** Teardown is a call's fuel less the same call ended by `os._exit(0)` after a flush:

| teardown | dev | 175 | 175 and 176 |
|---|---|---|---|
| bare call, plain | 39,103,919 | 23,309,529 | 19,765,098 |
| bare call, snapshot | 53,282,184 | 40,138,490 | 33,764,842 |
| `import numpy`, plain | 91,629,469 | 75,081,973 | 65,273,262 |
| `import numpy`, snapshot | 97,674,583 | 84,307,107 | 72,829,945 |
| a pandas groupby, plain | 314,769,515 | 298,043,391 | 254,188,159 |
| a pandas groupby, snapshot | 321,558,276 | 305,777,772 | 259,798,438 |

Over 175, this specification saves 3.5 M of a bare plain call's teardown and 6.4 M of a bare snapshot call's: under Decision 8's 8 M, since 175's kept dict was most of what the hook would have skipped there. So the bounds are restated with the measured figures, a claimed judge change: a bare call's teardown at most 22 M plain and 36 M snapshot (19.8 M and 33.8 M measured). Both fail on 175's set (23.3 M, 40.1 M) and on dev's. After a pandas groupby it saves 43.9 M plain and 46.0 M snapshot.

**The wrappers' cost**, calls ended by `os._exit(0)`, 175's set against both: a bare call 111,968,568 → 112,369,548 plain (+0.36%) and 1,412,836 → 1,421,407 snapshot (+0.61%); a pandas groupby 4,741,868,973 → 4,751,508,169 (+0.20%) and 4,460,318,703 → 4,470,531,059 (+0.23%). The snapshot's bare call is above 0.5%, so the rule applies: each whole call uses less fuel than before, a bare call 135,278,097 → 132,134,646 plain and 41,551,326 → 35,186,249 snapshot, a pandas groupby 5,039,912,364 → 5,005,696,328 and 4,766,096,475 → 4,730,329,497. The four rows record these calls' fuel, and the news file claims the growth. A fifth call, measured by the pull request's review, is not a net saving: an allocation churn that holds little at its end, 4,153,737,054 → 4,169,801,552 plain (+0.39%) and 4,166,800,598 → 4,176,852,980 snapshot (+0.24%), from 175's set to this one; against `dev`, 175's start saving covers it (snapshot 4,180,056,929 → 4,176,864,591). The news file's CHANGELOG line and `fuel.md` say so.

**The budget, counted.** An unshipped counting copy of the plain reactor (`TEARDOWN_BUDGET` unbounded, no drain, a count of the bytes asked through the wrappers while armed, printed after `Py_FinalizeEx`) ran the memo's nine programs: at most 13,587 bytes (the six imports); criterion 2's programs: a bare call 7,355, `import numpy` 21,599, a pandas groupby 65,729, 200,000 finalizers 7,355, 200,000 cycles 6,946, a session's shutdown 7,571. None is over 256 KiB, so B stays 1 MiB. Programs that do heavy work in teardown pass B and drain, as designed: a finalizer that imports (`__del__` of a cycle that imports, 12.8 MB asked), a stdout whose flush fails (34.0 MB: the traceback's printing), tracemalloc started in a finalizer (213 KB).

**Criterion 2.** Teardown's growth was 0 bytes in every row on both binaries, a session's shutdown included, and under the 64 MiB limit every room row ended with its lines, exit 0 and no exception ignored. The failed `new` (128 KiB of room) ends with `MemoryError: std::bad_alloc` in stderr, exit 0, no trap. **Seen failing** on three unshipped plain variants built from this recipe: with no budget and no drain, the NULL before the budget, the no-limit churn (memory grew past the bound), and both rows of an allocation past the budget; with the budget counted in the hook alone (the wrappers passing through), the Pillow row, as the review's R1 predicted; with the hook armed at installation, the `atexit` handler's row (917,504 bytes).

**Criterion 1, 3, 4.** After `run` and after `shutdown`, on both binaries, every export refuses (`run` 70, the rest −1) in under 10,000 fuel; these rows hold today's refusals, which pass on dev's set too. Criterion 4: neither binary imports `thread-spawn` and its one memory is not shared (flags 0), read from both with the judge's parser.

**Criterion 5.** All 45 probes, `sess.py`'s session and three tracemalloc probes (tracing at the end, stopped by an `atexit` handler, started in a finalizer) equal native CPython 3.15.2's outcome on both binaries. Against an ending in `os._exit(0)` after a flush, 37 of the probes and the session fail on both binaries. Those that pass against it include P11 and P19: native's callback does not fire, and neither does an `os._exit` ending, so they guard the other direction.

**The binaries.** On both, the only direct callers of `malloc`, `calloc`, `realloc` and `aligned_alloc` are their `__wrap_` functions (`posix_memalign` is linked only behind its wrapper); none of the five is in the function table, exported or named by `ref.func`; only `sbrk` grows the memory, and its callers are `dlmalloc` and mimalloc's `_mi_prim_alloc`, compiled in and never selected. On dev's binary `malloc`, `free` and `realloc` were in the function table, and the row fails there.

**Where the build differs from the text.**
- **numpy's data is in the raw domain.** numpy 2.5.4's default data handler allocates with `PyMem_RawMalloc` (`numpy/_core/src/multiarray/alloc.c:352`), so its frees are skipped too, against Decision 6. Criterion 2's row of an allocator outside the domains uses Pillow's image memory, which comes from `calloc`; a second row keeps numpy. In both the finalizer drops a 10 MiB block itself, then asks for 4 MiB with 1 MiB of room: CPython 3.15 finalizes every object of `__main__`'s namespace in one collection before it frees any, so a block held by `__main__` beside the finalizer is still alive when the finalizer runs, natively too.
- **The `atexit` rows** churn 64 KiB a hundred times, after the program takes every free 64 KiB block the heap has and frees one. With 1 MiB pieces the first request passes the budget and drains, so a hook armed too early could not be told from today's.
- **Room 0**: a heap full to its last bytes ends with CPython's own `Exception ignored while restoring builtins: MemoryError` on the plain binary, on dev's set as on this one; the row asks its lines and exit 0, and stderr only MemoryError lines.
- **The session probe**: native ends `sess.py`'s code with three files, not four: the finalizer's `open` runs after the builtins are gone (`NameError`, "Exception ignored"), natively and in the guest.
- **The function table's order.** The fast tier's first run on the rebased set failed `test_callbacks_have_the_types_cpython_calls`: the linker numbers the table in the order it meets functions' addresses, the hook's four functions, taken in code, came first, and FreeType's BDF property table, which the scan reads as a method at table index 1, then met `skipping_free`, of another type, where it had met `let_go`. The hooks are now a static table of `PyMemAllocatorEx`, data like `reactor_functions`, and index 1 is `let_go` again; the scan passes, the judge unchanged. Review round 1's Low 4: a row, `test_no_hook_sits_where_the_callback_scan_reads_a_method`, finds the hooks by name and fails if one sits at table index 1 or what sits there lacks a method's type; it failed on the first build's binaries (`skipping_free` at 1) and passes. Recognising FreeType's record by its name in the scan itself is left to a later judge change.
- The hook's state is the phases `FREES_RUN`, `FREES_SKIPPED` and `FREES_RUN_AGAIN`; `free_nothing_at_teardown` checks tracemalloc through `_tracemalloc.is_tracing()` and treats an error there as tracing.

**Rebased onto `a0b1171d`.** On the set built whole with this branch (175's landing notes give its hashes and bytes), against `dev`'s at `a0b1171d` built over the same tree: a bare call 284,437,056 → 132,420,433 fuel plain and 54,840,044 → 35,202,086 snapshot; its teardown 19.8 M and 33.8 M, under the restated 22 M and 36 M; a pandas groupby 5,272,569,988 → 5,099,883,452 plain and 4,876,145,507 → 4,827,154,464 snapshot. Ended by `os._exit(0)`, the snapshot's bare call 1,413,754 → 1,420,748 (+0.49%) and its groupby 4,552,018,454 → 4,561,775,876 (+0.21%), against `dev`, whose plain start 175 also moves. The 142 rows of `test_v1_4_the_end_of_a_call.py` pass on both binaries; their largest fuel, 6.08 G, sets the file's cap in `tests/lint/budget.toml` at twice that.
