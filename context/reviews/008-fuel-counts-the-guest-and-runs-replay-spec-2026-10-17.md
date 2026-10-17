# Review of 008 — Fuel counts the guest only, and a run can replay exactly (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read the constitution,
  `AGENTS.md`, `context/README.md`, the reviews README, the 006 pre-build review (for its format),
  the specification, the three memos it stands on, the fuel experiment's scripts, and the code it
  changes. I did not rely on the author's summary.
- **Reviewed:** `context/specifications/008-fuel-counts-the-guest-and-runs-replay.md` (draft,
  100 lines, untracked), against the working tree at `7116620`. The runner is as of `46cbc2f`.
- **Ran (EXECUTED, darwin-arm64, wasmtime-py 49.0.0, the 3.15 artifacts in `build/artifacts/`,
  read only).**
  - Scripts and outputs are under
    `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/review-008/`.
    Nothing under `build/` was written. No tracked file was edited.
  - `drv.py` is a driver built the way the specification describes. Its engine has
    `consume_fuel` and `epoch_interruption`, as the runner's does. It answers `clock_time_get`
    like the judge, and `random_get` with SHA-256(seed ‖ counter). With `remedy=True` it calls
    `set_fuel(2**63 - 1)` before `instantiate` and `set_fuel(cap)` after it. The module is either
    compiled in the process or loaded with `deserialize_file`. Every run gets a fresh root.
  - Probes `p1_repeat.py` to `p8_rate.py`, each with its `.txt` output. They are quoted in the
    findings.
  - I did not run `uv run pytest`. It writes under `build/`, which this review must not touch.
    The scoreboard is the build review's job.
- **Read (READ):**
  - our code: `src/wasi_python/runner.py`, `tests/harness/guest.py`, `tests/checks/conftest.py`,
    `tests/checks/test_v1_3_data_stack.py`, `tests/checks/test_v1_4_embedding.py`,
    `tests/unit/test_guest.py`, `tests/harness/wasm.py`, `tests/jobs/pandas_csv.py`,
    `recipes/reactor_main.c`, `recipes/reactor_bootstrap.py`, `context/progress/accepted.json`;
  - wasmtime v49.0.3 (`context/prior_art/wasmtime-v49`):
    `crates/wasmtime/src/runtime/store.rs:1478-1512, 1877-1907`;
    `crates/wasi/src/p1.rs:1282-1300, 2318-2395`; `crates/wasi/src/clocks.rs:100-175`;
    `crates/wasi/src/filesystem.rs:342-372`; `crates/wasi/src/filesystem/unix.rs:105-130`;
  - wasmtime-py 49.0.0: `_store.py:61-90`;
  - CPython 3.15.0: `Modules/timemodule.c:2228-2269`, and
    `cross-build/wasm32-wasip1/pyconfig.h` (`HAVE_CLOCK_NANOSLEEP 1`);
  - wasi-libc: `libc-bottom-half/cloudlibc/src/libc/time/clock_nanosleep.c`.

## What holds (the questions I was asked to look hard at)

- **`set_fuel` is an absolute set, and 2**63 − 1 is safe.**
  - READ: wasmtime's `set_fuel` overwrites both the injected counter and the reserve
    (`store.rs:1497-1512`). It caps the injected part at `i64::MAX` and puts the rest in the
    reserve, so 2**63 − 1 is exactly the largest single injection.
  - READ: wasmtime-py passes the value straight through (`_store.py:61-75`).
  - EXECUTED: after the reset, `fuel - get_fuel()` counts only what ran after `instantiate`.
- **`_initialize` stays metered.**
  - READ: both the runner (`runner.py:216-218`) and the driver (`guest.py:216-223`) call it
    after `instantiate` returns. So it runs after the reset.
  - EXECUTED, `p1`, the plain reactor running `-c pass`:

    | metering | compiled in the process | `deserialize_file` |
    |---|---|---|
    | today | 246,762,705 | 241,716,432 |
    | from after instantiation | 241,716,432 | 241,716,432 |

    The difference is 5,046,273, the image charge exactly. So the constructors were still
    counted.
  - EXECUTED: instantiation alone costs exactly `image + 1`: 42,352,641 for the snapshot and
    5,046,273 for the plain reactor. wasmtime-py's `Linker.instantiate` therefore runs no
    `_initialize`.
  - The specification should still say this in words (finding 8).
- **Nothing else runs guest code at instantiation.**
  - EXECUTED: neither binary has section 8. Both have sections
    `[0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 13]`, parsed with `tests/harness/wasm.py`.
  - The only other work at instantiation is wasmtime's own:
    - element segments and constant expressions;
    - the memory fill.
  - Their charge is exactly the image, as measured.
- **Decision 1 makes `fuel_used` independent of the module's source.** EXECUTED, `p1`. With the
  remedy, compiled and `deserialize_file` give identical counts:

  | program | count (compiled = loaded) |
  |---|---|
  | snapshot `-c pass` | 81,903,103 |
  | the `-u` hard-exit program | 2,905,270 |
  | the pandas golden job | 777,773,971 |
  | plain `-c pass` | 241,716,432 |

  Today's compiled count minus the remedy's count is exactly 42,352,641 for each snapshot
  program, and 5,046,273 for the plain reactor.
- **The fixed clock and random cover what CPython draws from entropy.** EXECUTED, `p5`, two runs
  with seed 0 and one with seed 1.
  - These match between the two seed-0 runs and differ with seed 1:
    - `os.urandom`;
    - `uuid4`, and `uuid1`'s random node;
    - `random.random()` (reseeded by `_refresh`);
    - `numpy.random.random()`, and an unseeded `default_rng()` (SeedSequence);
    - `tempfile` names.
  - These are constant:
    - `getpid()` returns 42;
    - `hash('abc')`, because the snapshot's secret is fixed at build.
  - The plain reactor's hash secret comes from `random_get` after `run()` unpins (READ,
    `reactor_main.c:272-279`), so it follows the seed.

## Acceptance criteria against evidence

1. *The three checks exist and were seen failing before the change.* **Not reachable as
   written.**
   - `test_no_start_section` guards a property that already holds, so it cannot fail first.
   - The cache check, as described, cannot fail inside one process (finding 5).
   - The replay check can fail first, but it would also fail at random afterwards (finding 1).
2. *Green; metrics drop by their binary's charge; accepted with `--accept-judge`.* Checkable,
   with two exceptions (finding 7):
   - the runner's metric runs on the real clock;
   - a rare residual from inode numbers.
3. *A dry run of the release workflow passes.* Checkable.

## Findings, most severe first

1. **Fuel, and so the record, does not replay exactly across fresh roots. The replay check would
   fail at random** (`008:41-43`, `008:78-82`). High.
   - **What I saw (EXECUTED, `p1`, `p2`, `p3`, `p8`).** I ran the pandas golden job with the
     clock and random fixed, a fresh root each run, and the module from `deserialize_file`.
     - In `p2` it reported 777,773,971 five times and 777,773,937 once.
     - Fixing every mtime in the root (`os.utime`) did not remove the spread.
     - Bisected (`p3`), the spread is in `df.to_csv('/out/a.csv')`: 96,309,425 against
       96,309,408 in 1 of 8 runs. `pass`, a script, a file read, `read_csv`, the RNG block, the
       time zones and dateutil each repeat exactly.
     - Thirty fresh roots (`p8`) gave 96,309,408 once. That was the only run whose `/out`
       inode, as the guest sees it, had at most 60 bits. Every other run's `/out` had 61 to 64.
     - On one root reused eight times (`p4`), the count was always 96,309,425.
   - **Cause (READ, then INFERRED from the correlation).**
     - wasmtime-wasi reports `st_ino` and `d_ino` as a SipHash of the host's `(dev, ino)`, with
       fixed keys (`filesystem.rs:353-372`, `unix.rs:105-125`, `p1.rs:1609, 1965-2000, 2089`).
     - So every copy of a root has new inode numbers. EXECUTED, `p4`/`p5`: the same file had a
       different `st_ino` in every run.
     - A value below 2**60 fits in two 30-bit CPython digits. Above that it needs three. Code
       that touches the number takes a few more or fewer instructions.
     - wasmtime's own comment says the hash may also change with the rustc release used to
       build wasmtime.
   - **Consequence.**
     - Decision 4 promises the same `fuel_used` from "the same … starting root". That is not
       true for a copy of the root. It is true only for the same host files.
     - Because `fuel_used` is inside the record (Decision 5), the record differs too.
     - The specified check runs the golden job twice in fresh roots. INFERRED from `p8`'s
       1-in-30: it fails in roughly one pair in eight, a flaky judge.
     - Within the judge's 0.01% tolerance this residual is harmless (17 to 51 instructions).
       Only the *exact* claims break.
   - **Fix (pick one, and say why):**
     - (a) Keep `fuel_used` out of the record's digest. `Completed.fuel_used` still reports it.
       The check asserts that stdout, files and record are identical, and that fuel agrees
       within the judge's tolerance. The README says that fuel replays exactly on the same host
       files, and to within tens of instructions on a copy, because inode numbers are host
       facts.
     - (b) Keep fuel in the record and narrow the promise to "the same host files". The check
       then reuses one root. That is awkward: the first run's outputs are in the second run's
       root.
     - (c) Make the runner answer the filestat and readdir calls itself. wasmtime-py cannot
       call the shadowed originals, so this means re-implementing the filesystem. Out of scope.
   - I recommend (a). In every case, Decision 4's not-replayed list gains inode numbers
     (finding 3).

2. **Decision 5's claim, "equal records ran the same program on the same inputs", is broader than
   what the record covers** (`008:49-54`). High.
   - The record leaves out these inputs, and each one changes the result:
     - **The stdlib zip.** The plain reactor imports every module from it, and the snapshot
       imports from it whatever it did not pre-import. `run(artifacts=…)` lets a caller pair a
       binary with any zip (READ, `runner.py:124-130`, `_place_stdlib`). Include its SHA-256, or
       the MANIFEST's.
     - **The wasmtime version.** Fuel costs are wasmtime's: 49.0 changed the cost of constant
       expressions (the research memo). The inode hash depends on wasmtime's rustc. Two
       wasmtime versions can give different `fuel_used` for the same run. The progress record
       already keys fuel by wasmtime version (`tests/unit/test_scoreboard.py:46`).
     - **The deterministic scheme.** This is the clock's start and step, and the random
       stream's construction. A later runner that changes either replays nothing. Put a
       version tag for the record's format in the encoding, and bump it with any such change.
     - **The limits.** `fuel`, `memory_bytes` and `output_bytes` decide whether a run traps or
       truncates. `truncated` is part of the outcome and is not in the list.
     - **The door.** The principal engineer's direction 6 asked for "the door transcript"
       (READ, memo line 418). A running SHA-256 over each request and response in `_door`
       costs a few lines. Without it, two runs whose host answered differently can share a
       record whenever stdout happens to match.
     - **The root.** The specification says this one out loud. But the sentence "the same
       inputs" still claims it.
   - **Fix.**
     - Add the zip's digest, the wasmtime version, a format tag, the three limits, `truncated`
       and a door digest.
     - Say what the record covers when `root=None`: the root is then fully determined (the zip
       and an empty `/tmp`).
     - Reword the claim: "equal records: the same binaries, arguments, environment, stdin,
       seed, limits and door traffic, ending the same way. A root the caller granted is the
       caller's to hash."

3. **Decision 4's list of what does not replay is incomplete, and one item is wrong**
   (`008:43-48`). Medium.
   - **Missing (EXECUTED unless marked):**
     - Inode numbers (finding 1).
     - **`clock_res_get`.** It is not shadowed. It passes through the host's resolution
       (READ, `p1.rs:1282-1300`, `clocks.rs`): 1 µs here (`p5`); Linux reports its own value;
       on Windows wasmtime reports 55 ms for the wall clock. `time.get_clock_info(...).resolution`
       therefore differs between hosts. It is cheap to shadow with a fixed 1 µs, the fake
       clock's step.
     - **Directory listings.** `fd_readdir` returns the host filesystem's order (READ;
       INFERRED: ext4's order is hash-based, APFS's is not).
     - **Directory metadata.** A directory's `st_size` and `st_nlink` come from the filesystem
       (`p4`: `/out` reports size 160 and nlink 5 on APFS).
     - **Filesystem behaviour.** Case sensitivity, error codes, name limits and free space are
       the host's (INFERRED).
     - **Fuel across wasmtime versions** (finding 2).
   - **Wrong: "`time.sleep` (it waits for real; the guest's clock does not move with it)".**
     - READ: CPython 3.15 on WASI sleeps with
       `clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, …)` (`timemodule.c:2269`;
       `HAVE_CLOCK_NANOSLEEP 1`). It computes the deadline from the guest's own monotonic
       clock, which is the fake one.
     - READ: wasmtime turns an absolute monotonic deadline into a wait until *its* monotonic
       clock reaches that value. That clock counts from the creation of the WASI context
       (`clocks.rs:119-172`, `p1.rs:2374-2390`).
     - So the wait is `deadline − real time since the context was made`. It is not the
       requested time. EXECUTED, `p6`:

       | program | fixed clock | real clock |
       |---|---|---|
       | `time.sleep(1)` | waits 1.03 s; the guest sees 2 µs pass | 1.02 s |
       | about 3 s of work, then `time.sleep(1)` | 3.41 s in all: the sleep is skipped | 4.41 s |
       | a loop that sleeps 0.05 s until 0.5 s have passed | 250,000 iterations, 1,285,399,246 fuel, 6.96 s | 10 iterations, 82,646,535 fuel |

     - The guest's output still replays, but the run is far from "waiting for real". A polling
       wait, common in retry and backoff code, spins for about `t / 2 µs` iterations. Under a
       fuel cap it can trap where the real-clock run would not.
   - **Fix.**
     - With `deterministic=True`, shadow `poll_oneoff` as well, for subscriptions that are all
       clocks: advance the fake clock to the earliest deadline, write that event, and return
       without waiting. CPython's `time.sleep` and `select`/`poll` with no descriptors both
       arrive here as a single clock subscription (READ, wasi-libc `clock_nanosleep.c`).
     - For a mix with descriptor subscriptions, choose and state one answer (for example
       `ENOTSUP`). The shadow cannot hand them to wasmtime's own implementation.
     - Or keep it out of scope and state what actually happens: the guest's clock moves 1 µs
       per reading; a sleep waits at most its time, and less once the run has been going that
       long; a loop that waits for the clock spins.
     - Either way, the README sentence changes.

4. **The record's canonical encoding and the random stream are not specified to the byte**
   (`008:35-40`, `008:49-52`). Medium.
   - "A SHA-256 hex digest over a canonical encoding" leaves open:
     - the field order and names;
     - how integers, `None` and strings are written;
     - whether `argv` includes `ARGV0`;
     - how `stdin=None` and `b""` compare;
     - the order of the environment's pairs;
     - what `trapped` holds. For a guest trap it is the message's first line, which comes from
       wasmtime's text and can change between versions.
   - Two implementations, or two runner versions, would disagree.
   - Return the canonical bytes, not only their hash. A hash alone cannot say *which* input
     differed, and it cannot be re-run from. Direction 6's done-when speaks of "a `Record`
     whose hash matches".
   - "A SHA-256 counter stream seeded by `seed`" does not say which bytes are hashed. It also
     does not give the seed's range, or whether `seed=0` equals the judge's stream (the judge
     hashes the counter alone, `guest.py:102-111`).
   - **Fix.**
     - Write the encoding down. For example: UTF-8 JSON with `sort_keys`, separators `(",",
       ":")` and `ensure_ascii=False`, with a `"format": "wasi-python-record/1"` key.
       - `argv` as given to WASI, `ARGV0` included.
       - `env` as a sorted list of pairs.
       - `stdin` as the SHA-256 of the bytes, with `None` treated as `b""`.
       - `trapped` reduced to a stable category: `"out of fuel"`, `"deadline"`, `"trap"`,
         `"error"`.
     - Expose it as `Completed.record` (the bytes, or a frozen dataclass) and
       `Completed.record_digest`.
     - Define the stream: block `i` = SHA-256(`seed` as 8 bytes little-endian ‖ `i` as 8 bytes
       little-endian), with `0 ≤ seed < 2**64`.
     - Say that `seed` without `deterministic=True` is a `ValueError`.

5. **The cache check, as described, passes before the change too, and its fuel is noisy**
   (`008:78-80`). Medium.
   - **The process memo hides the cache.** `_module` keeps the module by `(metered, digest)`,
     whatever `cache_dir` is (READ, `runner.py:506-510`).
     - A first call with `cache_dir=False` compiles and keeps the module.
     - A second call in the same process gets that same module back. It never loads a
       `.cwasm`, and none was written.
     - The two counts are then equal before and after the change. The check cannot be seen
       failing, and it would test nothing.
   - **The real clock adds noise.** Without `deterministic=True`, two runner calls differ by
     thousands of instructions (the principal engineer's memo: 4,132 on 1.0 G, EXECUTED there).
   - **Fix.**
     - Run each call in a fresh process, as `_cache_probe` already does
       (`test_v1_4_embedding.py:214`).
     - Assert `stats()` shows `compiled == 1` in the first and `loaded == 1` in the second.
     - Pass `deterministic=True`.
     - Use a program that touches no inode (`-c pass` repeats exactly: `p2`).
     - It fails today on macOS by 42,352,641 (EXECUTED, `p1`). On Linux it passes today
       (memfd), so criterion 1 is "seen failing on macOS".

6. **The replay check's seed clause is vacuous, and the check leaves its own conditions unstated**
   (`008:80-82`). Medium.
   - **The seed clause proves nothing.**
     - The seed is itself an input to the record, so a `seed=1` run has a different record
       whatever the job does.
     - The pandas job seeds its own generator, `np.random.default_rng(0)`
       (`tests/jobs/pandas_csv.py`). So "when the job draws random numbers" never tests the
       stream.
   - **Fix.**
     - Assert that the *stdout* differs, with a program that prints `os.urandom(8).hex()` and
       an unseeded `numpy.random.default_rng().integers(...)`.
     - The check must also:
       - pass `deadline_s=None` and a `fuel` cap (otherwise `fuel_used` is `None` and the
         60-second default is a wall-clock input);
       - give a `root`, so the files can be read back;
       - follow finding 1 on how fuel is compared.

7. **Decision 6's "exactly its binary's charge" fails for two known reasons, and "before" needs
   a definition** (`008:55-59`). Low-medium.
   - **Most metrics drop by exactly the charge.** The driver's metrics come from `guest.run`
     with the clock and random fixed. They drop by exactly 42,352,641 (snapshot) or 5,046,273
     (plain). EXECUTED for four programs, `p1`.
   - **Exception 1: `test_a_cpp_exception_reaches_python`.** It records the *runner's* fuel
     (`test_v1_3_data_stack.py:127-140`), on the real clock and real entropy. Its after-figure
     moves by the charge plus noise.
     - Have it pass `deterministic=True` (and drop `cache_dir=False`, as the research says).
     - Or list it as the one metric measured on the real clock.
   - **Exception 2: inode-touching programs.** These can move by tens of instructions
     (finding 1). Such a move is well inside 0.01%, and it should not trigger an
     "investigation".
   - **"Before" must be measured on the same build.** The accepted figures in
     `context/progress/accepted.json` come from an earlier commit. The snapshot's
     `test_guest_runs_here` is 124,270,847 there, against 124,255,744 for my `-c pass` today.
     So the landing notes' before-and-after pairs must both come from this build, run by the
     judge with and without the driver change.
   - **Tight metrics.** `test_unbuffered_output_survives_a_hard_exit[snapshot]` falls from
     about 45.26 M to 2,905,270 (EXECUTED). Its 0.01% band becomes ±290 instructions. It
     repeated exactly in `p1`, and it touches no inode, so that is fine. Name it in the landing
     notes as the tightest metric.
   - The judge's metrics are keyed by platform (`darwin-arm64`), so Linux's figures, which
     never had the charge, are not disturbed.

8. **Decision 1 must say when it applies and what it still meters** (`008:22-29`). Low.
   - **The unmetered engine.** `Store.set_fuel` raises "fuel is not configured in this store"
     on the runner's unmetered engine (READ, `store.rs:1895-1899`). The reset belongs inside
     `if fuel is not None`.
   - **A run without a cap.** Say what `record` holds for `deterministic=True` with
     `fuel=None`: `fuel_used` is `None` then. Or say that `deterministic=True` without a cap is
     allowed and is recorded as `null`.
   - **`_initialize` stays metered.** Say that `_initialize` (the plain reactor's constructors)
     is guest code and is metered, because it is called after `instantiate`. That is what the
     code does (EXECUTED above), but the decision's wording, "from the end of instantiation",
     invites the opposite reading.
   - **The cost of the free fill.** The unmetered fill is bounded by the binary the *caller*
     chose (`artifacts=`), never by the guest. Say so, since spec 006 made "safe by default"
     a property.

9. **The fake clock's answers for other clock IDs are unspecified** (`008:35-37`). Low.
   - The judge's `clock_time_get` answers success for every clock ID.
   - wasmtime answers `BADF` for the two CPU-time clocks and `INVAL` for unknown IDs (READ,
     `p1.rs:1295-1297`).
   - wasi-libc emulates CPU time from the monotonic clock (`p5`: no ID 2 or 3 was asked), so
     this barely shows today.
   - **Fix.** Specify it anyway. IDs 0 and 1 are faked; 2 and 3 return `BADF`, as in real
     mode; anything else returns `INVAL`. Then the two modes differ only in values, never in
     errors.

10. **`test_no_start_section` cannot be seen failing** (`008:30-34`, `008:92`). Low.
    - It is the same pattern as finding 7 of the 006 pre-build review: the property already
      holds.
    - **Fix.**
      - Either run its assertion once against a WAT module with a `(start …)` and record
        that it failed,
      - or exempt guard checks from criterion 1 in the specification's words.
    - A cheaper and stronger check of Decision 1 itself, for the driver's unit tests: a WAT
      reactor with one page of data and one with none report the same `fuel` for the same
      export. It fails on macOS today (by 16,385, the research's `image_size.py`).

## Constitution checks

- **§4.4 holds.** Shadowing `clock_time_get`, `random_get` (and `poll_oneoff`, `clock_res_get`
  if adopted) changes only the host's answers. The guest's imports are unchanged.
- **§4.5 holds.** Nothing names an embedder.
- **§4.9 holds, if finding 6's fix lands.**
  - The specified checks compare counts and bytes.
  - The replay check must pass `deadline_s=None`, or the wall clock becomes an input.
  - My `p6` timings are probe facts here, not checks.
- **§4.10:** the specification's numbers all trace to the research memo's executed runs.
  Decision 4's `time.sleep` sentence is an unlabelled claim, and it is wrong (finding 3).
- **§5.2 (no open questions):**
  - the record's encoding is undecided (finding 4);
  - the stream's construction is undecided (finding 4);
  - the cap-less deterministic case is undecided (finding 8).
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

The specification is narrowed to its fuel half (Decisions 1 to 4); deterministic replay moves to
`research/2026-10-17-what-a-replayable-run-needs.md`, a placeholder that records findings 1 to 4,
6 and 9 as what an experiment must answer.

1. **Answered by the split.** Replay is not promised; the inode effect is in the memo. The cache
   check compares within the 0.01% tolerance, not exactly.
2. **Answered by the split.** The record's contents (the zip's digest, wasmtime's version, a
   format version, the limits, `truncated`, the door's traffic) are listed in the memo.
3. **Answered by the split.** The memo states the `sleep` behaviour, `clock_res_get`, directory
   order and sizes, inode numbers and timestamps.
4. **Answered by the split.** The memo requires an encoding fixed to the byte and the encoded
   record returned.
5. **Fixed.** Decision 3 runs the cache check in fresh processes and asserts a load via `stats()`.
6. **Answered by the split** (no replay check).
7. **Fixed.** Decision 4 re-measures the "before" figures on this build and names the two
   exceptions.
8. **Fixed.** Decision 1 says the reset applies only with a cap, and that `_initialize` stays
   metered.
9. **Answered by the split.**
10. **Fixed.** Decision 2 adds a WAT module with a start section to see the rule fail; Decision 3
    adds the data-page unit test.

## Verdict

**Does not build yet.** Decision 1 is right, cheap and proven exact. The replay half needs
changes before it is built:
- its exact-fuel promise breaks on any copy of a root (finding 1);
- its record claims more than it covers (finding 2) and is not defined to the byte
  (finding 4);
- its `time.sleep` sentence is wrong (finding 3);
- two of its three checks cannot be seen failing as written (findings 5 and 10).

One line: metering from after instantiation is correct and removes exactly the image charge,
but a replay's fuel still moves with the root's inode numbers. Take fuel out of the record's
exact claim (or narrow it to the same host files), complete and pin down the record, and fix the
sleep sentence and the two checks before building.
