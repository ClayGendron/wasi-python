# Review of 176 — The end of a call frees nothing

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude), a fresh sub-agent of Claude Code session 0672b924-ca3c-4b6c-91ca-f834537cb1bc; not the author
- **Reviewed:** the specification as drafted, `context/specifications/176-the-end-of-a-call-frees-nothing.md` (uncommitted), with its memo `context/research/2026-10-31-a-lighter-exit.md` and its evidence folder, the `decisions.md` entry, the roadmap sentence and specification 175, on `research/a-lighter-exit` at `59013cf3`
- **Run:** none: a specification review
- **Re-ran:** one `uv run python` script through the memo's driver (`build/lx/drv.py`, spec/167's set): linear memory at the end of a call that makes and drops an 8 MiB `bytearray`, against `pass`, each ending in `os._exit(0)` → snapshot 41,943,040 to 43,384,832 bytes (+1,441,792); plain 41,943,040 both. A `diff` of `Python/pylifecycle.c:2270-2620` between CPython 3.15.0 and 3.15.2 → identical. With this file written, `uv run pytest tests/lint -q` → 14 passed. No `gh` call, no run dispatched.
- **Time box:** 45 minutes (the build recipe); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning. The CPython read is the pinned 3.15.2 (`downloads/SHA256SUMS:16`), from a sibling worktree's `build/Python-3.15.2`.

## Acceptance criteria against evidence

1. **(a) No instance runs after its teardown** — holds, READ. Every line cited matches (`reactor_main.c:511, 516, 561, 626, 726, 749, 752, 767, 778, 806, 868`; `hostmodule.c:25-29`; `_call.py:293-298, 546-549`; `_sessions.py:637-660, 954-956`). After `run`, each export refuses before any Python: `resume_if_restored` returns at once because `checkpoint` refused to enter after `run`. After `shutdown`, the same, on `shut` or `turned`. A restored checkpoint and a prepared image end through `end_prepared` and never finalize. The host makes one store per call and closes it on every path. A session's store closes in `_release_session`. The only pool in `src/` is a thread pool (`_process.py:123-126`); no instance or store is reused. The criterion's rows are sound.
2. **(b) Teardown's memory, against the cap** — not met as designed (Findings 1 and 2).
3. **(c) The hook arms only after `atexit`** — holds, READ. `make_pre_finalization_calls` (`pylifecycle.c:2273-2376`) loops thread shutdown, pending calls and `_PyAtExit_Call` until none is left. Only then does `_Py_Finalize` set the runtime's finalizing state (`:2418-2419`), which `Py_IsFinalizing` reads (`:153-156`). The flushes of `sys.stdout` and `sys.stderr` (`:2461`, `:2491`), collection 1 (`:2480`) and `finalize_modules` (`:2484`) run after frees stop. This is by design and harmless: each `tp_dealloc`, `__del__`, weakref callback and file flush still runs in full, and only the last `PyObject_Free` or `PyMem_Free` is skipped. No byte written depends on a free. The memo's 45 probes ran on a spike that skipped every free, libc's included, for the whole call, so they cover the hook a fortiori (INFERRED).
4. **(d) Threads** — holds in substance. The wording is wrong (Finding 5).
5. **The probes** — sound. Each row is seen failing first against an `os._exit` ending, which shows the row discriminates.
6. **The cost, as counts** — sound before 175. After 175, the bound is a guess (Finding 4).
7. **The run** — standard.

Every check counts fuel, bytes or outcomes. None reads a clock.

## Findings, most severe first

1. **High: Decision 3's headroom is wrong three ways, and its proof (b) rests on it** (`176:§3`).
   - (i) **The probe grows memory on every snapshot call, so criterion 2's first bound fails.** wasi-libc's `sbrk` never shrinks linear memory. An 8 MiB `malloc` that does not fit the free space grows memory for good, even after it is freed. EXECUTED: on a bare snapshot call it grew linear memory by 1,441,792 bytes. Criterion 2's first row allows 256 KiB.
   - (ii) **"R more stays free for allocations that do not pass through the hook" is false.** Allocations through the hook use the same `malloc`. While frees are skipped, each one draws fresh memory, from that same R first. The fallback fires only when an allocation *through the hook* gets `NULL`. Between that moment and the point where free memory is gone, any allocator outside the hook can get `NULL` where native would reuse a freed block. Outside the hook are: numpy's data handler (Decision 6), sqlite's own `malloc` during P29's rollback, OpenBLAS's emulated mmap (`60_link.sh:91`), `host_alloc` for a door call made by a finalizer, and C++ `new`. Failure: on a heap near its cap, a finalizer that builds a `bytes` and then a numpy array raises `MemoryError`, giving "Exception ignored" where native prints its line. C++ `new` aborts on failure in this toolchain, which traps (INFERRED).
   - (iii) **Peak memory has no bound below the cap.** Frees resume only on a `NULL`. A finalizer that allocates a lot in total, such as pickling a large frame from a `weakref.finalize`, keeps every temporary. It grows the instance toward the cap before the fallback fires: 1 GiB by default (`__init__.py:71`), or 4 GiB with `memory_bytes=None` (`_call.py:441`). Native would peak near the frame's size.

   Fix text, Decision 3: "Arming takes no probe and no reserve. While armed, the hook counts the bytes asked of it (`malloc`, `calloc`, `realloc`'s new size). It threads each skipped block onto a list through the block's own first word, as dlmalloc's own `free` writes there. When the count passes B (1 MiB), or an allocation through the hook gets `NULL`, the hook frees every block on the list, stops skipping and, on a `NULL`, tries once more. Teardown then draws at most B more than native at any moment, for every allocator, and the bare call's memory does not grow." B is 8 to 16 times the measured teardown growth (`out-memory.tsv`), so no normal program reaches it. If the author keeps a probe, criterion 2's first bound must be restated with the measured growth, and (ii) and (iii) still need the budget.
2. **Medium: criterion 2 has no row that would catch Finding 1.** Its rows allocate only through the hook and never pass R in total. Evidence that would close it: rows under `memory_limit` 64 MiB, each equal to native and never trapping. (a) Finalizers that alternate 1 MiB `bytes` with a 1 MiB numpy array, near the cap. (b) A P29-style uncommitted sqlite insert, near the cap. (c) With no limit, a finalizer that makes and drops 1 MiB 500 times, whose growth stays within B plus 64 KiB.
3. **Low: tracemalloc takes the hook away.** `_PyTraceMalloc_Stop` puts back the allocators it saved (`tracemalloc.c:919-921`). It runs from an `atexit` `tracemalloc.stop()`, before arming, or from `_PyTraceMalloc_Fini`, late in teardown. Frees then resume. That is harmless, but Decision 4's "the hook stays installed after `Py_FinalizeEx`" is not always true. Fix text: Decision 4 adds "unless tracemalloc, stopping, restores the allocators it saved, after which frees run as today". Criterion 5 gains a probe in which `tracemalloc.start()` runs and the outcome equals native.
4. **Low: the bound after 175 is not measured** (`176:§8`, criterion 6). "Its base's figure less 8 M" is unlabelled. 175 removes the frees of the zip's dict (about 2 k fuel per member, 8,191 members), which are part of the 18.5 M, so what is left to save is unknown. Fix text: "INFERRED; the builder that lands second measures both together. If the saving left is under 8 M, the bound is restated in the landing notes with the measured figure, as a claimed judge change."
5. **Low: the CPython read and criterion 4 need restating.** The specification cites 3.15.0 and the set pins 3.15.2. The finalization range is identical (EXECUTED diff), so cite 3.15.2. `pyconfig.h:2021` defines `WITH_MIMALLOC`. All three domains still use `malloc` because `obmalloc.c:440-443` chooses `MALLOC_ALLOC` without pymalloc or free threading, and the isolated config ignores `PYTHONMALLOC`; Decision 1 should say so. Criterion 4's "defines no thread support" is not literally true: `thread.c:60-66` compiles `thread_pthread.h` against wasi-libc's single-threaded pthreads. Fix text: "The guest imports no `thread-spawn` (EXECUTED: none in the spike binaries) and its memory is not shared, so `pthread_create` fails and one thread runs. wasip1 delivers no asynchronous signal (`HAVE_SIGACTION`, `HAVE_ALARM` and `HAVE_SETITIMER` undefined), and a deadline traps and discards the store."
6. **Low: a write-in on the hook's state.** If any probe stays, "never arms" needs a state that is never cleared, so a failed probe is not retried on every free. Its "three plain statics" is really three saved allocators plus its own state. The raw-domain `free` must not need an attached thread state; `Py_IsFinalizing` meets that.
7. **Low: names.** The `START_FACTOR` check is called 073's here and 069's in the memo and at `reactor_main.c:407`. Pick one. The check (`test_v1_3_data_stack.py:230`, `snap.fuel * START_FACTOR <= plain.fuel`) does hold: the snapshot loses a larger share than plain.
8. **Low: Decision 9 drops an option the owner leaned toward.** The owner wrote "I think offer as opt-in", then "do what is best for the project". The specification reads the second as leave to drop the first. The reason is good, but this was not asked as a choice. Fix: put it to the owner with the AskUserQuestion tool, with "drop it" recommended, before the build's pull request, and record the answer in `decisions.md`.

## Constitution checks

- **Kind:** build-class and a judge change, reviewed before it is built (§5.6). Right: the hook is compiled into both binaries.
- **Not structural:** holds. Nothing under `src/` changes. The state lives in `recipes/reactor_main.c`. The harness fields are in `tests/`. The new check file must name no specification in its comments.
- **The judge change is honest:** two harness fields are added, plus a new file with a cap by `budget.toml`'s rule. No existing check, golden output, allowance or `START_FACTOR` is edited.
- **§4.1:** a recipe on public API (`PyMem_SetAllocator` wrapping the existing allocator, `memory.rst:561`); no patch. **§4.9:** counts only. **§4.6:** `MANIFEST` and `SHA256SUMS` change, and criterion 7 claims them.
- **§7:** nothing tripped.
- **175:** compatible. 175's `stdlib_directory` is a reference, not code run after teardown, and both edit `reactor_main.c` near `:561` and `:767`, so the second to land rebases. With 175, `START_FACTOR` becomes 2 and still holds.
- **Roadmap:** the 0.1.3 paragraph repeats a block twice ("…cairo").Two decisions of 2026-10-30…"). That was already on `dev` and is not this change's, but whoever next edits it may clear it.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Taken, as the fix text. Decision 3 now takes no probe and no reserve: a 1 MiB budget of bytes asked while armed, skipped blocks threaded through their first word, every list freed past the budget or on a `NULL`, then one retry. It states the bound (the budget plus one allocation above today), the residue for allocators outside the hook, the smallest block (dlmalloc's 16-byte chunk, 12 usable; zero-size requests ask `malloc(1)`), and why all three domains pass through the hook. The budget rests on a new native measurement, `tally/` (at most 55,243 bytes asked in ten programs), and the build counts it in the guest.
2. Taken. Criterion 2 gains rows for a `NULL` before the budget, allocators outside the hook (numpy data and C++ `new`) near the cap, a sqlite rollback near the cap, and churn with no limit, whose growth is bounded by the budget.
3. Taken. Decision 4 names tracemalloc's restore; criterion 5 gains two tracemalloc probes.
4. Taken. Decision 8 labels the bound INFERRED, unmeasured until the second of 175 and 176 lands, and says what restates it.
5. Taken. CPython 3.15.2 cited; Decision 1 gives `obmalloc.c:440-443` and the isolated configuration; Decision 5 and criterion 4 take the fix text.
6. Taken. Decision 3 lists the state, with a phase never left; Decision 2 notes `Py_IsFinalizing` needs no thread state.
7. Taken. Called 069's check (b).
8. Settled: the owner left this to the project ("do what is best for the project and what makes this production ready", 2026-10-31), and the orchestrating session dropped the opt-in. Decision 9 and `decisions.md` say so.
- R1. Taken, fix (a). The link wraps `malloc`, `calloc`, `realloc`, `aligned_alloc`, `posix_memalign` and musl's `__libc_malloc` and `__libc_calloc`. While armed, every byte counts toward B, the drain runs before an allocation would cross B, and any `NULL` drains and retries once. The bound is now B for every allocator. Nothing infeasible was found; the builder confirms from the link map that only dlmalloc calls `sbrk`, and any other gets fix (b). Criterion 2 gains the example as a row; criterion 6 records the unarmed wrapper's fuel.
- R2. Taken: the `RendererAgg` row and its failed-`new` row; the text now says libc++ is the exceptions build, so `new` throws `bad_alloc`.
- R3. Taken: no hook when tracemalloc is tracing at install (Decision 1).
- R4. Taken: re-run with `atexit = False`; `finalize` still never calls back after `atexit`, so the row is dropped and the count is nine programs.

## Re-review of the amended specification, 2026-10-31

Read: the amended specification, its Disposition, and `tally/` (`tally.c`, `native_tally.py`, `out-native-tally.tsv`). Also checked: the cross files (`recipes/wasi-*.cross`) for C++ flags, and `reactor_main.c` and CPython 3.15.2 as before. Re-ran: nothing new, since the native tally reads plainly.

**The earlier findings.**

- **1: answered for allocations through the hook.** The probe and the keep-back are gone, so a bare call no longer grows memory, and criterion 2's first bound can hold. While frees are off, the bytes asked through the hook are counted and capped at B. With no limit, the churn row's growth is bounded by B, and the tally shows a drain (`skipped 857 drained 1`). Allocations outside the hook remain open, below as R1.
- **2: taken, with a gap.** The new rows are buildable but for the C++ one (R2), and none of them reaches R1's case.
- **3 to 7: taken as written.**
- **8: settled.** As the coordinator directs, this is not a finding. Decision 9's last sentence and Disposition 8 still say the drop "is put to the owner". They should say the owner left it to the project, as `decisions.md` records.

**The questions asked.**

- **Can the list be corrupted?** Not by any valid use (READ, INFERRED).
  - A skipped block is never handed back to dlmalloc, so its address cannot be returned again while it is on the list. Nothing aliases.
  - `realloc` of a live block while armed goes straight to the saved allocator. If the block moves, dlmalloc frees the old one inside itself, not through the hook, so the list never sees it.
  - `realloc` of a block already skipped is a use after free, undefined natively too.
  - A **double free** makes the list a cycle: X → Z → X. At the drain, the second `free(X)` fails dlmalloc's in-use check and aborts, a trap. Blocks skipped before X's first skip are cut off and never freed. Natively, the same double free aborts at the second free. The class is the same; only the moment moves.
  - A free into another domain's list still ends at the same `malloc`.
- **What does realloc do while frees are off?** The hook counts the new size, so a shrink is counted too, which is conservative. When `realloc` returns `NULL`, the old block is still valid, so the drain and one retry are correct. Decision 3 should say both in a sentence.

**Findings of this round.**

- **R1. Medium: the bound "for every allocator" is not true.**
  - **What the spec claims.** Decision 3's bound and residue say an allocator outside the hook is short by at most "the bytes asked so far".
  - **Why it is wrong.** Those allocators are not counted. They cannot reuse skipped blocks. Their `NULL` never reaches the hook, so it never drains. Their shortfall is therefore what the hook skipped, up to every byte module teardown freed, not B.
  - **What fails.** A teardown allocation outside the hook that is larger than the free memory the program left at its last line. Native would reuse the skipped blocks.
  - **Example.** Under `memory_limit` 64 MiB, the program ends with 1 MiB of room. `__main__` holds a 10 MiB `bytes` and, defined after it, an object whose `__del__` makes a 4 MiB numpy array. Module teardown frees the `bytes`, and the hook skips it. Then numpy's `malloc` gets `NULL`: "Exception ignored … MemoryError" where native prints the line.
  - **Why criterion 2 misses it.** Its outside-allocator row interleaves 256 KiB pieces, and its budget drains first.
  - **Fix (a), recommended.** The link wraps `malloc`, `calloc`, `realloc`, `aligned_alloc` and `posix_memalign`, as it already wraps others (`60_link.sh:170`). While armed, a `NULL` from any of them drains and retries once. Criterion 6 records the wrapper's fuel on a bare call and a pandas groupby, since every `malloc` of every call pays it.
  - **Fix (b).** Decision 3 states the residue as above. Criterion 2 gains the example as a row expecting that difference. `docs/reference/limitations.md` names it.
  - **Closed by** either fix and the example's row.
- **R2. Low: the C++ row is not concrete, and my Finding 1 was wrong about C++.**
  - **The correction.** The cross files compile C++ with `-fwasm-exceptions -fexceptions` (`wasi-matplotlib.cross:39`, `wasi-pandas.cross:31`), so a failed `new` throws `bad_alloc` rather than aborting. That holds unless the libc++ linked in was built without exceptions.
  - **Fix text.** "In a finalizer, `matplotlib.backends.backend_agg.RendererAgg(256, 256, 72)`, whose constructor allocates its 256 KiB pixel buffer with `new[]` (the builder cites `src/_backend_agg.cpp`). The row asserts its line and exit 0. A second row, with 128 KiB of room, establishes what a failed `new` does in this build: `MemoryError` or a trap. The answer is written into Decision 3's residue."
- **R3. Low: tracemalloc at install strands the lists.** When a program is tracing at the end, the hook wraps tracemalloc's. `_PyTraceMalloc_Fini` then restores the originals, after which no `NULL` reaches the hook. The skipped blocks stay skipped through `finalize_interp_clear`, which allocates little. Fix text: "When `tracemalloc` is in `sys.modules` and `is_tracing()` is true before the call, the hook is not installed."
- **R4. Low: one tally row measures the wrong phase.** "weakref.finalize pickles 50 MB" runs at `atexit` (`finalize.atexit` is true by default), before arming. Its 35,547 bytes show the pickle never ran in teardown. Set `atexit = False` on the finalizer and re-run, or drop the row from "ten programs".

### Verdict of the second read
Fit to build once R1 is answered, by fix (a) or (b), with the example's row. Findings 1 to 7 of the first round are taken. R2 to R4 are Lows the builder may take with the build.

In one line: the budget and the threaded list are sound and cannot be corrupted by valid use, but allocators outside the hook neither count nor drain, so the "every allocator" bound needs a `malloc` wrap or an honest residue.

## Third read, 2026-10-31

Read: the amended Decisions 1, 3, 4 and 9, criteria 2, 5 and 6, and the Disposition. Checked against wasi-libc in the prior-art clone at `165235b`: `dlmalloc/src/dlmalloc.c`, `expected/wasm32-wasip1/defined-symbols.txt`, `libc-top-half/musl/src/include/stdlib.h` and `libc-bottom-half/sources/sbrk.c`. Also checked `60_link.sh:170` and `:210-216`.

**R1, fix (a): taken, and it closes the Medium.** Every `malloc` now counts, a `NULL` from any allocator drains the list and retries, and the drain runs before an allocation would cross B. So the bound holds for allocators outside the Python hook too. My numpy example is a row.

**Does `--wrap=__libc_malloc` catch musl's calls?** Yes (READ).
- **Where the callers live.** `__libc_malloc`, `__libc_calloc` and `__libc_free` are aliases of `malloc`, `calloc` and `free`, defined in `dlmalloc.c:97-99`. Their callers are other objects: `locale/newlocale.c`, `duplocale.c`, `locale_map.c`, `dcngettext.c`, `time/__tz.c` and `exit/atexit.c`. In those objects the symbols are undefined, declared `hidden` in `src/include/stdlib.h:13`. `--wrap` rewrites undefined references by name, and hidden visibility does not stop it in a static link.
- **Calls inside one file.** The only translation unit that both defines and calls an allocator is `dlmalloc.c`. Inside it, calls go through the static `dl*` names, under an outer call that was already counted.
- **What does not exist here.** `__libc_realloc` and `memalign` are not defined for `wasm32-wasip1`. `reallocarray` is defined in its own object and calls `realloc`, which is wrapped.
- **Function pointers.** References taken by address, such as numpy's `&malloc` handed to its cache, are relocations against the same undefined symbol, so they are rewritten too.
- **No LTO.** No step builds CPython or the libraries with LTO; matplotlib and the plot libraries set `-Db_lto=false`. So no bitcode escapes the rewrite.
- **The one way it fails.** It fails silently only if some object defines its own allocator and calls it. That is the mechanical check proposed in L2 below.

**Can `realloc` or `aligned_alloc` push teardown past B?** Not past the bound's sense. The count and the heap differ in three small ways.
- **`realloc`.** It counts the new size before the call. Growing in place uses less than that. A move frees the old block inside dlmalloc, a real free that today's teardown also makes. A shrink is counted in full. All of these over-count, which is safe. A `NULL` leaves the block valid, so the retry is sound.
- **`aligned_alloc` and `posix_memalign`.** dlmalloc takes the size plus the alignment, then gives back the leading and trailing pieces at once (`dlmemalign`). The surplus returns to the free bins, where later counted allocations reuse it.
- **Chunk overhead.** This is the real gap (L1). The count is bytes asked, but the heap spends whole chunks: the request plus 4, rounded up to 16, with 16 the least. A teardown of 1-byte requests could hold up to 16 times B. Python's requests are rarely under 16 bytes, so the realistic factor is under 2. Teardown stays bounded and far from the cap either way, but "at most B" is not what the code as written guarantees.

**R2, R3, R4: taken.**
- **R2.** The link checks that libc++ and libc++abi are the exceptions build, `eh/` (`60_link.sh:214-216`). So "`bad_alloc`, expected as `MemoryError`" is right. The `RendererAgg` row is concrete: 256 × 256 × 4 bytes is 256 KiB.
- **R3.** Moot as well as taken: the drain now runs in the C library's wrappers, so a hook removed by tracemalloc no longer strands the lists.
- **R4.** The row is dropped, honestly: "nine programs".

**Lows of this read**, none blocking:
- **L1. Count chunks, not bytes asked.** Fix text, Decision 3: "Armed, it adds the chunk each request takes: `max(16, (n + 4 + 15) & ~15)`, plus the alignment for `aligned_alloc` and `posix_memalign`." The bound then holds as stated.
- **L2. Turn the coverage into a check.** Fix text, Decision 3's "What could escape": "Over the linked `python.wasm`, a build check asserts two things. The only direct callers of the functions `malloc`, `calloc`, `realloc`, `aligned_alloc` and `posix_memalign` are their `__wrap_`s. None of those functions is in the function table." This catches an object that defines and calls its own allocator, as `sbrk`'s list does for memory.
- **L3. Say what happens past 0.5%.** Criterion 6's 0.5% for the unarmed wrapper is INFERRED, and the criterion does not say what happens if it is exceeded. Fix text: "Above 0.5% the figure is recorded and claimed, and the build lands only if the whole call, teardown included, uses less fuel than today for both a bare call and a pandas groupby on both binaries." That keeps the change a net saving, which is its point.
- **L4. Fix the failed-`new` row's state.** With 128 KiB of room, the `NULL` drains whatever is on the list and retries. The row then records a failure only if nothing drainable is held. Fix text: "The finalizer runs first, with the list empty, so the retry fails as native's would; the row asserts no trap and records the outcome."
- **L5. Two Decision 9 sentences say the same thing.** "The owner leaned towards it, then left the choice to the project." and "The owner left this to the project (…)" repeat each other. Keep the second.


**Closing read, at `8d8af3a8`.** L1 to L5 are taken, each checked against the committed specification.
- **L1.** The chunk formula, `max(16, (n + 4 + 15) & ~15)`, matches this build's dlmalloc (READ). wasi-libc's `dlmalloc.c` leaves `FOOTERS` at 0 (`malloc.c:631`), so `CHUNK_OVERHEAD` is one `size_t`: 4 bytes on wasm32 (`:2213`). `MALLOC_ALIGNMENT` is 16, so `CHUNK_ALIGN_MASK` is 15 (`:1623`). `MIN_CHUNK_SIZE` is 16. `pad_request` is `(n + 4 + 15) & ~15`, and `request2size` gives 16 below `MIN_REQUEST` (`:2222-2241`).
- **L2** is a row that reads the linked binaries.
- **L3.** The 0.5% rule now says what happens above it: the whole call must use less fuel than today.
- **L4.** The failed-`new` row runs with the list empty.
- **L5.** The repeated sentence is gone.

## Verdict
Lands: the specification as committed at `8d8af3a8` can be built. Every High, Medium and Low of the three reads is taken, the wrap covers every allocator in the link, and the budget is counted in dlmalloc's real chunk sizes.

In one line: teardown runs whole, frees nothing within a 1 MiB budget counted across every allocator, and drains back to today's heap before it could ever cost a trap.
