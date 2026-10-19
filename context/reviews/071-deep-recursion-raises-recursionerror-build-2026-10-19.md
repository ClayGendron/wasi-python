# Review of 071 — Deep recursion raises RecursionError (the build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5). I reviewed the specification before it was
  built (`../071-review/…-spec-2026-10-18.md`, with its confirmation). I wrote none of the
  code, checks or notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/071-deep-recursion-raises-recursionerror` at `3b41afe`, on main `b413192`
  (055 landed). Commits: `d200e49` (checks and judge changes), `a1098a3` (code), `18a471d`,
  `0ffbfba`, `2658b83` (the session row), `682fabd` (055's seam), `e831e47` (the `Turns`
  driver's deadline) and `3b41afe` (notes). The set is the worktree's `build/artifacts/`:
  `SHA256SUMS` `618247d2…` (EXECUTED: `shasum`), `python.wasm` `c44ca042…`. I copied it to
  `set071/` beside this file and ran every probe against that copy. Main's set
  `s-9d43bf645dfcaa71` was read only, and copied to `setmain/` for the containers.
- **Ran (EXECUTED).** Nothing was written in any git tree or in the main tree's `build/`.
  Probes and logs are in `probes/`:
  - **Fast tier.** `uv run pytest -m "not slow" -n 3` in the worktree, against 071's set
    (`fast-n3.log`, `fast-n3-latest.json`): `491/545 pass · 0 gap · 3 blocked · 0 fail · 51
    deselected`; `1755 passed, 10 skipped`; ratchet lost 0, gained 53, grew 58.
  - **Full judge.** `uv run pytest -n 3` in the worktree (`full-n3.log`, `full-n3-latest.json`):
    `528/545 pass · 14 gap · 3 blocked · 0 fail (unit suite 1264/1271, 7 skipped)`; `1792
    passed, 10 skipped, 14 xfailed in 580.44s`; `ratchet vs 1dbf2c831f: lost 0 · absent 0 · unrun
    0 · unrun locally 1 · gained 53 · grew 71`. This reproduces the builder's run. numpy-core:
    +1,081,482,057 against the builder's +1,081,373,954.
  - **The fault-handler orders.** `border.sh` and `bchild.py`, with `chain.c` from my
    confirmation probes, run 15 orders through the built `wasi_python`, each in its own process.
    They ran on Debian glibc 2.41 and Alpine musl, on aarch64 and x86_64 (four logs,
    `orders-{glibc,musl}-{arm64,amd64}.log`).
  - **Criteria 1, 2 and 4 on x86_64 Linux.** `crit_x86.py` runs the checks' own `RECURSIONS`
    and `LIMITS` through `wasi_python.run` there (`crit-amd64.log`). The judge never runs them
    on that host.
  - **The calling thread.** `thread_stack.py` runs a guest that uses its whole stack on a
    default Python thread, on all four Linux configurations and on macOS
    (`thread-stack-linux.log`, `thread-stack-darwin.log`). `thread_musl.py` splits the musl case
    by guest and runner, for branch and main (`thread-musl.log`).
  - **The growth.** `coerce_probe.py` and `split_host.py` (spec 047's, copied unchanged) run
    on main's set and 071's set through the worktree's driver (`coerce_probe.txt`,
    `core-main.tsv`, `core-071.tsv`, `core-compare.txt`).

## What holds

- **The recipe line (READ).** It is exactly the specified call, right after
  `Py_InitializeFromConfig`, with `C_STACK_WINDOW` and `__stack_high` beside `__stack_low`, and
  it aborts on failure. 055's exports merged beside it without a conflict. `recipes/patches/`
  is untouched. The plain binary grew 283 bytes.
- **Decision 9 as built behaves as my confirmation probes predicted, on every Linux
  configuration (EXECUTED, four logs, identical outcomes on glibc and musl and on both
  architectures).**
  - **Traps returned, host alive:** never enabled, enabled before the first call, enabled
    after and then disabled, and a chaining native handler installed before the first call.
  - **Refused with the message, host alive:** enabled after; enabled before and disabled after;
    `signal.signal(SIGILL, …)` after; `signal.signal(SIGSEGV, …)` after; a chaining native
    handler after (the conservative refusal the README now states); a non-chaining one after;
    `run_async` after.
  - **The session seam (`682fabd`), host alive in every case:**
    - opening a session after a late enable is refused;
    - a turn after a late enable is refused, the session ends with `ended == "error"`, and
      `shutdown_outcome == "skipped"`;
    - closing a session whose handlers were replaced after its last turn skips the ending's
      shutdown export (`"skipped"`), where on main that ending runs guest code with a broken
      chain.
  - **The code (READ).** `_trap_handlers_ready` compares load bases (`dladdr` of
    `wasm_engine_new`), counts `SIGFPE` on x86_64 only, treats any exception as not ready, and
    is the first thing `_drive` does, before `_check_preopens` runs its wasm. It also runs at a
    session's opening, at the top of `_drive_turn` and in `_shutdown`. Every entry follows an
    engine's creation, so wasmtime's handlers are already installed when it reads them.
- **An epoch callback at full depth is harmless (EXECUTED).** A `run(cancel=Event())` whose
  guest spins for a second at its deepest recursion takes epoch callbacks every 50 ms from the
  bottom of the native stack. It ends `RecursionError 207 Stack overflow (used 112 kB)`, exit 0,
  on glibc x86_64 and musl x86_64 and aarch64. The glibc aarch64 run had my probe's first,
  wrong program.
- **The judge's driver matches the runner's metered engine (READ; EXECUTED by criterion 5's
  unit).**
  - `engine()` sets `consume_fuel`, `epoch_interruption` and `max_wasm_stack = 512 KiB`, the
    three settings `_engine(True)` makes and nothing else. The runner's unmetered engine (`run`'s
    default, `fuel=None`) has smaller frames, so the judge is on the thin side.
  - **The far-off deadline hides nothing new (READ, INFERRED).** The `Turns` driver's
    `2**40`-tick deadline only keeps the driver's never-ticking engine from interrupting at
    deadline 0, which is the "wasm trap: interrupt" `e831e47` fixed. The driver had no epochs
    before 071, so it never exercised the runner's epoch callback, and still does not. The
    runner's own `Session` checks do exercise it.
  - **Fuel.** The engine change moves no fuel that I could find: on main's set through the new
    driver, numpy-core's split total equals its accepted fuel plus the door calls my split adds
    (202,446,711,432 against 202,357,454,477; 20,259 door calls).
- **Criteria 1, 2 and 4 hold on x86_64 Linux, through the built runner (EXECUTED,
  `crit-amd64.log`: bad 0).**
  - All 36 criterion-1 runs pass, at depths equal to arm64's: `__repr__` 214, `heapq` 244,
    lxml 67/82/86/77. Messages are "used 112 kB", except `sorted-key` at 113 kB, which is why
    the pattern accepts both.
  - All six criterion-4 pairs pass.
- **The departures are each sound (READ, EXECUTED where marked):**
  - criterion 1's 112-or-113 kB pattern (113 seen above);
  - the Python-handler row using `SIGILL`, because a stack-overflow trap raises `SIGILL` (a late
    `SIGSEGV` handler is refused all the same, EXECUTED);
  - `own=(engine, module)`, because a store needs the module's engine;
  - the three `test_highly_nested` variants, by id (`v3/evidence/test-ordered-dict-variants.txt`);
  - the check at a session's opening, because opening runs the preopen-check module's wasm.
- **The judge and the CPython suite.** The full judge loses nothing. The CPython-suite comparison
  (27,534 passes against 27,503) is the builder's, on the first build. The recipe hunk is the
  same; the only loss is `test_ordered_dict`'s three variants and the only gain
  `test_functools`, as Decisions 7 and 8 say.

## Findings, most severe first

### F1 (medium). A new README sentence is false on musl; following it can kill the host

The README's new paragraph under *Running it* says "Python's threads have about 2 MB or more on
every host".

- **What happens (EXECUTED, `thread-musl.log`).** On Alpine, musl's default thread stack is
  128 KiB, and `threading.stack_size()` reports 0, the default. A `wasi_python.run` on a default
  thread whose guest recurses (`lru_cache`, which raises `RecursionError` on the main thread)
  kills the host with SIGSEGV (exit 139), on aarch64 and x86_64. So does `run_async` on its own
  default pool.
- **What still works.** `print` and `import numpy` on such a thread work. With
  `threading.stack_size(1 << 20)` set first, the same recursion raises `RecursionError`.
- **Not a regression, and not a crash elsewhere.** Main's runner and set crash the same way
  (EXECUTED, the `main` rows). On glibc (both architectures) and macOS, default threads run the
  same guests to `RecursionError` and the trap (`thread-stack-*.log`).
- **What 071 adds.** The sentence is 071's, and Decision 9's promise ("a guest trap cannot end
  your process") reads as covering this case.
- **Asked:**
  - Correct the sentence: musl gives threads 128 KiB, so set `threading.stack_size(1 << 20)` or
    more before the runner's first `run_async` and before making threads that call `run`.
  - Name the case under *Not protected*.
  - Optionally, record as a follow-up (question 102's neighbour) that the runner makes
    `run_async`'s pool itself and could give its threads a stack.

### F2 (low). Criterion 4 guards the roomier engine, not the one the README's numbers come from

- **The mismatch.** Criterion 4 calls `run` at its defaults, so it runs unmetered
  (`fuel=None`, READ, `runner.py:368`). The README's limits and Decision 5's edges were
  measured on the metered engine.
- **What it changes (EXECUTED, `crit-amd64.log`).** On x86_64 through the unmetered runner,
  the unbounded `ElementTree`-target case raises `RecursionError` at 122 instead of trapping.
  The check's `either` flag accepts that, so it passes either way.
- **Asked:** pass `fuel=` in criterion 4, as criterion 1 does, so it holds the thin case.
  Otherwise, say in the README that the limits are those of a metered call and that a call
  without `fuel` reaches a little further.

### F3 (low). `Session.shutdown_outcome`'s docstring misses the new reason for "skipped"

It still lists "stopped mid-turn, no turn ever ran, or `shutdown_s` was 0" (READ,
`runner.py:4856–4860`). The README's *Safety* line names the new reason. Add "or wasmtime's
trap handlers were replaced (Linux)".

### F4 (low). The `--accept-growth` reason names the wrong cause

The landing notes attribute numpy-core's +1.08 G to layout in general ("hashing by id, the
allocator's arenas, the collector's timing") and to past swings. The cause is narrower,
measurable, and the same one spec 047's delta measured:

- **The bool type's address (EXECUTED, `coerce_probe.txt`).** CPython's static type objects
  sit 64 bytes higher in 071's snapshot: `bool` at `0x15c5598` against `0x15c5558`, and `str`,
  `complex`, `list`, `np.ndarray` and `np.float32` all move by `0x40`. `np.array` of 131,072
  Python bools, four times, costs 669,301,880 fuel on 071's set against 642,039,204 on main's
  (+27,262,676, +4.25%). The other types are within ±0.02%: int and float, which numpy checks by
  pointer, and complex, str and `np.float32`, which take the same dict path but are unchanged.
  numpy looks each Python scalar type up in a dict keyed by the type's address, and bool's new
  address costs more there. These are the very numbers of spec 047's delta (642 M against
  669 M).
- **Where the growth lands (EXECUTED, `core-compare.txt`).** Through the judge's own session
  and drive script, with a door call per line, numpy-core grows +1,177,938,498 per test in
  sum. The 108 `test_strings.py::test_string_comparisons` cases account for +1,107,000,303 of
  it, about 10 M each (each builds 32,768-element bool lists and coerces them). Every other test
  moves by at most ±1.0 M, a net +54.6 M, which is the door calls my split adds costing slightly
  more on 071's set. The judge's own figure is +1,081,482,057, so it is all
  `test_string_comparisons`.
- **The rest (EXECUTED, `full-n3-latest.json`).** Every other fuel metric moved by at most
  +0.155% / −0.162%. The plain binary grew 283 bytes.

Corrected reason, for the lane:

> `--accept-growth "spec 071's rebuilt python.wasm and snapshot (one recipe call; plain +283
> bytes) move CPython's static type objects by 64 bytes; numpy looks up each Python bool's DType
> in a dict keyed by the type's address, and bool's new address costs more there (np.array of
> 131,072 bools +4.25%; int, float, complex, str and np.float32 within ±0.02%), so numpy-core
> grows +1.08 G (+0.53%), all of it in test_strings.py::test_string_comparisons (108 cases, about
> +10 M each), the cause spec 047's delta measured; every other fuel metric within ±0.17%"`

### Notes (no change asked)

- **N1.** A refused turn ends the session (`"error"`), though no guest code ran and the
  interpreter is sound. The message's remedy (`faulthandler.disable()`) then cannot save that
  session. This is the specification's choice ("ends as on an error") and is documented.
- **N2.** Criterion 11's `signal-after` row expects a returned trap on Windows. That is
  INFERRED (wasmtime's vectored handler runs before a CRT signal handler). The release's
  Windows dry run is the evidence (AGENTS.md 6b).
- **N3.** The CPython-suite comparison was made on the first build (`6cc30bb`). The lane's
  judge does not run that suite while 065 is off main, so it is not re-measured at landing, as
  the notes might suggest. The recipe hunk is identical, so I take it as standing.
- **N4.** My probe for an epoch callback at depth was wrong in its first glibc-aarch64 run
  (every level spun, so the call hit its deadline). The other three configurations ran the
  corrected program.

## Constitution checks

- §4.1: no patch; a recipe line through CPython's documented API (READ).
- §4.3: one window and one check for every host. The check is Linux-only by the platform's
  mechanism, not by a host branch in the guest (READ).
- §4.9: the new checks count depths, outcomes and fuel; none times anything (READ).
- §4.10: claims in the notes are labelled. The growth reason is corrected (F4).
- §4.11: the limits are documented; the musl thread limit needs a line (F1).
- §4.15: no default loosened. A call is now refused where it used to kill the host.
- §5.6: I re-ran the counted tests: the fast tier and the full judge, both `-n 3`.

## Verdict

**Lands once F1 is written in.** It is a README correction, and the lane can check it without
another review. F2 and F3 may be written in or answered in the landing notes. F4's corrected
`--accept-growth` reason above replaces the builder's.

The build does what the specification says, on every host I could run. Recursion through
Python code raises at the same depths on arm64 and x86_64; the documented limits hold. Decision
9 refuses exactly the orders that would kill or hang the host, on glibc and musl and on both
architectures, at a session's opening, turn and ending too. The judge loses nothing.

## One line

It lands once the README stops saying Python's threads have 2 MB everywhere (musl's 128 KiB
kills the host on a deep guest). The growth is bool's moved type address in numpy's type dict,
as in 047, not layout in general.

## Delta look after the rebase onto 069 (main `d900dd9`, set `s-1a7242a7a8b518f4`)

- **Date:** 2026-10-19. **Reviewer:** the same fresh agent.
- **Reviewed:** branch tip `17c6846` on `d900dd9`. The new set is the worktree's
  `build/artifacts/`, with `SHA256SUMS` `14ada22a…` (EXECUTED). The A/B sets are
  `build/artifacts-069recipe/` and `build/artifacts-fullwindow/`. I copied all three, read only,
  to `delta/` beside this file. Nothing was written in a git tree or in the main tree's `build/`.
- **Ran (EXECUTED; scripts and logs in `delta/`):**
  - `git range-diff b413192..a5349e0 d900dd9..76940b9`;
  - the product change lines before and after the rebase (`old.diff`, `new.diff`);
  - `wdiff.py`, `datadiff.py` and `strshift.py`, which compare the two plain binaries section by
    section, function by function, table slot by table slot, and by string-literal address;
  - `raise_probe.py`, run on 069's, 071's and the whole-window sets;
  - the fast tier with `-n 3` on the new set (`fast-n3.log`, `fast-n3-latest.json`).

### The rebase changed nothing else

- **The commits (EXECUTED).** All 13 reviewed commits are `=` in `git range-diff`, patch for
  patch, through `a5349e0` → `76940b9`.
- **The change itself (EXECUTED).** The `+`/`-` lines of `git diff b413192 a5349e0` and
  `git diff d900dd9 17c6846`, over `src`, `recipes`, `tests`, `README.md` and `CHANGELOG.md`, are
  identical: 889 lines each. `17c6846` adds only notes and evidence.
- **The post-review commit `76940b9` (READ).** It holds the build review's F1 to F3, as asked:
  - the musl paragraph under *Running it* and *Not protected*;
  - criterion 4 metered (`functools.partial(_run(), fuel=10**11)`);
  - `shutdown_outcome`'s new "skipped" reason, in the docstring and the generated reference.
- **The A/B base is exact.** The 069-recipe relink equals 069's frozen set byte for byte
  (EXECUTED: `SHA256SUMS` lines equal).
- **The handler check still runs first (READ, `runner.py` at `17c6846`).**
  - It is still the first statement of `_drive`, before the cancel check, `_check_preopens` and
    `linker.instantiate` (lines 2738–2740).
  - The session opening (4684), the turn (4394) and the ending (4210) keep theirs.
  - 076 added no new path into wasm: the only `instantiate` calls are the preopen check, `_drive`
    and the session's.

### The growth: measured, and its reason corrected

The builder measured the fuel correctly, and the A/B relink does isolate it to the link. But the
traced cause is not "a raised exception costs 17 more", and "data do not move" is not right.

- **What the link changes (EXECUTED, `wdiff-plain.txt`; `datadiff.py`; `strshift.py`).**
  - **Functions and the table.** One function is added, `PyUnstable_ThreadState_SetStackProtection`,
    at index 3732. Every later function's index shifts by one, so 26,477 same-named bodies differ
    in bytes but not in length; only the `call` immediates change. The function table keeps its
    order: all 22,261 slots point to the same functions, 20,527 of them renumbered by exactly +1.
    The new function is not in the table, so no function-pointer value changes.
  - **The data section.** It differs in 1,144,518 bytes at the same length. The new function's
    message, "stack_size must be at least %zu bytes" (38 bytes), enters `.rodata` at `0x101bfe4`,
    and **every C string literal after it moves 38 bytes**. "ordinal not in range(128)" moves
    from `0x10db585` to `0x10db5ab`, so its address mod 8 goes from 5 to 3; "ascii", "utf-8",
    "encoding" and "<string>" move the same way. Literals before the insertion point
    ("sOnns", "strict") do not move.
  - **What does not move.** The shift is absorbed before `.data` (`0x15c5290`, unchanged), so
    static objects and the heap stay put. That matches the builder's equal type addresses, and
    explains why numpy-core does not grow this time.
- **Raising costs nothing more; walking a moved literal does (EXECUTED, `raise_probe.txt`,
  65,376 iterations each, 069 against 071).**

  | probe | change per iteration |
  |---|---|
  | `raise ValueError` from Python | +0.14 (the fixed start cost of +9,458 to +9,522, spread over the loop) |
  | a `KeyError` from `{}[i]` (no literal) | +0.14 (the same fixed start cost) |
  | `'é'.encode('ascii')` raising `UnicodeEncodeError` (a literal reason) | +17.14 |
  | `int('x')` (a literal format string) | +282.14 |
  | `str()` of one `UnicodeEncodeError`, no raise at all | +21.14 |

  The whole-window relink gives the same numbers to the operator. So the cost follows code that
  walks a moved C string literal: an error's reason, or its format string. INFERRED: wasi-libc's
  word-at-a-time `strlen` and `memcpy` step byte by byte until the address is aligned, so a
  literal's new alignment changes their count. It can go either way per literal; here it is
  mostly up.
- **The rest.** The snapshot start's +9,586 (the `pass` probe, and about +9,000 on every
  snapshot-start check) is the same effect on literals walked during start-up (INFERRED). The
  lxml encoding checks grow most because they build tens of thousands of `UnicodeEncodeError`s.
  The builder's "function indices after it shift by one" is true, but it moves no operator.
- **The fast tier on the new set (EXECUTED).** `495/550 pass · 1 gap · 3 blocked · 0 fail · 51
  deselected`; `1763 passed, 10 skipped, 1 xfailed`; ratchet against `96cf575`: lost 0, gained
  53, grew 22. The largest fast-tier growth is +0.061% (snapshot starts). The binaries grew +219
  and +278 bytes, as noted. I did not repeat the full run; the builder's is 532/550, 0 fail,
  lost 0, grew 25.

Corrected reason, for the lane:

> `--accept-growth "spec 071's rebuilt python.wasm and snapshot link one more CPython function
> (PyUnstable_ThreadState_SetStackProtection; plain +219 bytes, snapshot +278); its 38-byte error
> message enters .rodata and moves every later C string literal by 38 bytes (static objects and
> the heap do not move), so code that walks such a literal, an error's reason or format string,
> spends a few operators more by its new alignment: a UnicodeEncodeError +17, a snapshot start
> +9,586, the lxml encoding checks up to +0.23%, every other metric at most +0.06%; raising itself
> costs nothing more, and a whole-stack-window relink grows the same, so it is the link, not the
> window"`

### Verdict on the delta

**Confirmed, it lands**, with the corrected `--accept-growth` reason above. The rebase is
patch-identical, the handler check still runs first in `_drive` after 076, and the A/B relink
pins the growth to the link. That growth is one moved block of string literals, not the window
and not raised exceptions as such.

### One line (delta)

The rebase changed nothing, and it lands. The growth is the new function's 38-byte message
moving every later C string literal: walking a moved literal costs more, raising does not.
