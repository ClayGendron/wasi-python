- **Project:** regex (https://github.com/mrabarnett/mrab-regex)
- **Against:** 2026.9.29 (the pinned tarball)
- **Status:** drafted
- **Title:** Keep timeout clock ticks in a 64-bit type, and treat a timeout too large for any clock as no timeout
- **Files:** src/_regex.c
- **Why we carry it:** on `wasm32-wasip1` `Py_ssize_t` has 32 bits and `CLOCKS_PER_SEC` is 10**9, so any `timeout=` above 2.147 s saturates to 2.147 s of ticks and then never fires: a match under `timeout=3` runs until the embedder's own limit.

**This is a facts sheet, not a pull request** (question 80 in `context/decisions.md`). The regex repository has no contributor guide and no rule on AI-written changes that the agent could find (READ, 2026-10-18, for spec 047's sheet; unchanged on 2026-10-19). Under question 80's recommendation, if you send it, you write the issue or pull request yourself from these facts. Nothing has been posted, and no agent will post anything to the project.

When spec 087 is built, this file moves unchanged to `context/upstream/patches/regex-2026.9.29/0002-timeout-ticks.md`, and `fix.patch` is copied byte for byte to `recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch`. The evidence stays in `context/upstream/24-regex-timeout-ticks/evidence/`, so every link below is a path from the repository's top. (The folder's number is the next one free across the open branches on 2026-10-19: 21 to 23 are taken by specs 037, 065, 078 and 085.)

**Checked for you** (2026-10-19): regex 2026.9.29 is still the newest release on PyPI; `src/_regex.c` on the default branch `hg` (head `0e8cb0596b`, 2026-09-28, "Updated to Unicode 18.0.0") is byte-identical to the 2026.9.29 release's, so the code below is unchanged there. GitHub's issue search for "timeout" finds no report of this. The nearest is #321 ("Timeout doesn't seem to work (at least on macOS)", open since 2019), which is a different matter: native `clock()` counts CPU time, so a callback that sleeps does not advance it.

## The facts

**The code.** `decode_timeout` turns the `timeout=` float into clock ticks, and `check_timed_out` compares elapsed ticks against them. Both use `Py_ssize_t`:

```c
/* src/_regex.c:21092 */
return value >= 0.0 ? (Py_ssize_t)(value * CLOCKS_PER_SEC) : RE_NO_TIMEOUT;
/* src/_regex.c:2258 */
if ((Py_ssize_t)(clock() - state->start_time) < state->timeout)
```

`RE_State.timeout` (line 519), the `timeout` parameters of `state_init_2`, `state_init` and `pattern_subx`, and the nine `tim` locals that carry the value are `Py_ssize_t` too. `start_time` is already a `clock_t`.

**Two failures follow, both from converting a double that does not fit.** C leaves the conversion of an out-of-range floating value to an integer undefined (C11 6.3.1.4), so what happens depends on the target's instruction:

1. **Where `Py_ssize_t` has 32 bits**, `value * CLOCKS_PER_SEC` passes `INT32_MAX` at 2,147.48 s with POSIX's 10**6 ticks per second, and at 2.147 s on WASI, whose wasi-libc defines `CLOCKS_PER_SEC` as 10**9 (and `clock_t` as `long long`).
   - **wasm32-wasip1** (EXECUTED). clang compiles the conversion to `i32.trunc_sat_f64_s` (`evidence/decode_timeout_wasm.txt`), which saturates at `INT32_MAX`. `check_timed_out` then compares the elapsed ticks, also cast to 32 bits, against `INT32_MAX`, which a 32-bit value never exceeds. So **every `timeout=` above 2.147 s never fires.** On a host clock that steps one millisecond per read, `timeout=2.147` raises `TimeoutError` and `timeout=2.148`, `2.2`, `3`, `5` and `1e9` run on until the fuel limit (`evidence/f3_driver_1ms_unpatched.out`). Under a real clock, `timeout=3` and `timeout=5` ran to the 12 s deadline (`evidence/f3_runner.out`).
   - **32-bit x86 and 32-bit ARM** (INFERRED, not run): x86's `cvttsd2si` gives `INT32_MIN`, after which any elapsed time compares as timed out, so a timeout above about 2,147 s fires at the first check; ARM's `vcvt` saturates, so it never fires, as on wasm32.
2. **Where `Py_ssize_t` has 64 bits**, a timeout beyond 9.22 × 10**12 s overflows the same way. That is no realistic wait, but `float("inf")` is a natural way to write "no limit".
   - **x86-64** (EXECUTED, regex 2026.9.29's own cp315 manylinux wheel in a linux/amd64 container, `evidence/native_x86_64.out`): `timeout=1e12` completes, while **`timeout=1e13`, `1e30` and `float("inf")` raise `TimeoutError` at once**.
   - **arm64** saturates (`fcvtzs`), so those values never fire: the same script on macOS arm64 completes for all five (EXECUTED, `evidence/native_arm64.out`).

**The change** (`fix.patch`, 26 lines in, 16 out, all in `src/_regex.c`):
- a `typedef long long RE_Ticks;` beside `RE_NO_TIMEOUT`, with a comment saying why;
- `RE_State.timeout`, `decode_timeout`'s return, the three `timeout` parameters and the nine `tim` locals become `RE_Ticks`;
- `check_timed_out` casts the elapsed ticks to `RE_Ticks` instead of `Py_ssize_t`;
- `decode_timeout` returns `RE_NO_TIMEOUT` for a value that is negative, NaN (as before), or whose ticks reach `LLONG_MAX` (new), and converts only values that fit.

It keeps the API, the pickled form and every result. It widens nothing that was already 64 bits. `long long` rather than `clock_t`, because `clock_t` is a 32-bit `long` on Windows (with 1,000 ticks per second), where it would narrow today's 64-bit `Py_ssize_t` on Win64.

**What it does not fix: 32-bit glibc.** There `clock_t` is a 32-bit `long` too, at 10**6 ticks a second. So `clock() - start_time` itself wraps past 2**31 ticks, about 2,147 s (36 minutes), with or without this change. A timeout above that still cannot fire there: with the change it never fires, where on 32-bit x86 it used to fire at once (INFERRED, not run). Fixing that needs a clock wider than `clock()`'s, a larger change than this one.

**How it was tested** (EXECUTED 2026-10-19, in a scratch folder: regex 2026.9.29 built for `wasm32-wasip1` with wasi-sdk 33's clang and linked into this project's CPython 3.15 reactor, under wasmtime 49; `evidence/relink.txt`):
- **The build reproduces before the change.** Without it, the rebuilt `_regex.o` and the relinked interpreter equal the released ones byte for byte. With it, the interpreter is 202 bytes larger.
- **It compiles clean.** No warning with the build's flags, and none on the changed lines under `-Wall -Wextra -Wconversion -Wshorten-64-to-32`. The conversion becomes a guarded `i64.trunc_sat_f64_s` (`evidence/decode_timeout_wasm.txt`).
- **Every timeout fires on time.** With it, `timeout=2.148`, `2.2`, `3`, `4.3`, `4.4`, `5` and `9` each raise `TimeoutError` after that many seconds of the guest's clock. `0` raises at once, as before. `1e9` runs on, as a wait of 31 years should. `1e30`, `inf`, NaN and `-1` mean no timeout (`evidence/f3_driver_1ms_patched.out`).
- **The same under a real clock.** `timeout=3` and `timeout=5` raised after 3.0 and 5.0 s (`evidence/f3_runner.out`).
- **Nothing else moves.** Starting the interpreter and importing regex take the same instruction count with and without it (`evidence/fuel.out`).

The scripts that produced each file are beside them (`f3_driver.py`, `f3_runner.py`, `f3_check.py`, `fuel.py`, `native_x86_64.py`). `make_0002.py` is the edit, written as exact replacements, from which `fix.patch` was taken with `git diff`.
