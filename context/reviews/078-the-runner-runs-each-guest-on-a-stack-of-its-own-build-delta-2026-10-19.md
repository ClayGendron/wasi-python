# Delta review of 078 — the answers to its build review, 2026-10-19

- **Reviewer:** the build review's author, a fresh agent who wrote none of 078.
- **Under review:** `git diff 7aa0c52..333d9bb` on `spec/078-the-runner-runs-each-guest-on-a-stack-of-its-own`:
  - `2a0a98d`, the fixes (15 files);
  - `333d9bb`, the landing notes' numbers (spec only).
- **Against:** my build review (`078-the-runner-runs-each-guest-on-a-stack-of-its-own-build-2026-10-19.md`, F1 to F11), and the spec's new section "Disposition of the build review".
- **How I ran it:**
  - the full judge on `333d9bb`, clean;
  - my F1 and abandoned-turn probes, unchanged;
  - the new `start-interrupted` child row against `7aa0c52`'s runner (`git archive` into scratch, `PYTHONPATH`) and against the fix.
  - Scratch: `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/078-buildreview/` (`probes/`).
  - I wrote nothing in any git tree.

Labels: **EXECUTED**, **READ**, **INFERRED**.

## Short version

- **F1 is fixed.** My probe, unchanged, now prints:
  - `guest threads alive when run raised: []`;
  - `closes while wasm ran: []`. The handshake is sound on every path an ordinary interrupt can take (section 1).
- **F7 and F8 are fixed.** **F2, F4, F6, F10 and F11 are answered as asked.** **F3 is the owner's, accepted.** **F9 is answered**, and it still matters to the lane (section 4).
- **The judge on `333d9bb`** gives 537/650 pass · 57 gap · 56 blocked · 0 fail, and a ratchet of lost 0 · absent 14 · gained 40 · grew 3. These are the builder's verdicts exactly.
- **What is left:**
  - The `--accept-judge` text has double quotes nested inside its double-quoted argument, so it breaks when pasted into a shell (D1).
  - The "exit −6 on `7aa0c52`" evidence line does not reproduce: four runs exit 0 with two bad closes (D2).
  - Two notes on the handshake's double-fault edges (D3).

**Lands once D1 is fixed** (a text edit in `context/`). D2 and D3 are notes.

## 1. F1: the start handshake (READ, EXECUTED)

- **What it does now.**
  - `_start_guest` takes `home.lock`, then sets `state="starting"`, `done=False`, the thread, `serving=True`, and clears `ended`.
  - It then calls `thread.start()`.
  - On an exception, under the lock, it cancels only a start the body has not taken (`starting` → `cancelled`, `done=True`, `ended` set).
  - The body takes the lock first. If the state is `cancelled` it returns at once; otherwise it sets `running`.
  - `_join_guest` waits on `home.ended`, which the body sets last, after any abandoned steps.
- **Each path checked:**
  - **Exception before the lock block:** the state is the previous `idle`, `done` is true and `ended` is set. Nothing to wait for. Correct.
  - **Exception inside the lock block** (a partial assignment): the `except` sees `starting` and cancels. Correct.
  - **`start()` fails before the OS made the thread:** cancelled. The call raises, and the teardown runs now. Correct.
  - **Interrupt in `start()`'s wait:**
    - if the body has already taken it, the state is `running`, and the home waits on `ended`;
    - if not, the start is cancelled, and the body returns at once, with no wasm and nothing touched. Both correct.
- **EXECUTED.**
  - `probes/start_interrupted-delta.out`: run raised only after the guest ended; no close under wasm.
  - The new child row on the fix: `interrupted`, `bad closes []`, `next 1`, exit 0.
  - On `7aa0c52`: `bad closes ['MainThread', 'MainThread']` in four of four runs. So the row is seen failing first, though not as the evidence says (D2).
  - `probes/abandoned_turn-delta.out` is unchanged and correct: busy held, the second turn refused, the session ends "error", the next session works.
- **The new units:** an interrupted start keeps its guest; a failed start is cancelled and a late body returns at once. Both assert the state as described.
- **Edges left:** D3.

## 2. F7 and F4's new rows (READ, EXECUTED)

- **F7.**
  - `serving` is now set inside the start's lock, before `start()`.
  - `_on_guest_thread` clears it after the join.
  - A cancelled start clears it.
  - `call` raises `_Stopped` without posting once `raised` is set.
  - `serve` answers a queued box with `_Stopped` instead of running it.
  - So no embedder code runs after the home has stopped. A stop raised by the home itself still answers its box in flight from `except`, as before.
  - The unit `test_a_stopped_home_answers_new_hand_offs_with_a_stop` covers both halves.
- **F4.**
  - **`relaxng-deep-tree`:** completes at 4,300, a quarter under 5,756. Traps at 9,000, 40.9% past 6,388. The grammar recurses one element per level, so the trap is in the validator.
  - **The session row** is my probe, made a check with exact lines.
  - **Criterion 18's child rows** land the interrupt through stand-ins for the inbox and the box, through a real `run` with a provider. That is a listed departure, and accepted: an exact bytecode cannot be hit otherwise.
  - **musl:** all five rows on 3.14.5 and 3.13.13, each system; 3.14.0 refused on each row.
  - **amd64 before the change:** all nine trap checks trap on main's runner.
  - All five new checks pass in my judge.

## 3. The other findings

- **F2:** answered.
  - The class's and the gap's `closes_with` now name a reserved roadmap entry, which states the folder and the zip step exactly.
  - The README calls it a current limit with the fix reserved.
  - The gap's digest is unchanged, as it should be.
- **F3:** the owner accepted the Linux price on 2026-10-19. The notes record the numbers the owner saw and a follow-up.
- **F5:** the content is now complete, but it is not paste-safe (D1).
  - Small: "those three gaps' digests restated". Two are restated; `no-missing-stdlib-info`'s is new.
  - The text no longer names the one-comment change in `test_v1_4_embedding.py` that the spec's own text had.
- **F6:** answered. `build/078/latest-full.json` holds 650 checks, on `2a0a98d`, `dirty: false`.
- **F8:** `_ask` and the inert stand-in are removed.
- **F10 and F11:** written in as asked.

## 4. The judge (EXECUTED)

`uv run pytest -n 3` on `333d9bb` (clean), with another judge running on the machine:

- `wasi_python v1: 537/650 pass · 57 gap · 56 blocked · 0 fail (unit suite 1598/1606, 8 skipped)`.
- `2135 passed, 64 skipped, 57 xfailed in 406.28s`.
- `ratchet vs b91e0eaa4e: lost 0 · absent 14 · unrun locally 42 · gained 40 · grew 3`.
- The five new gained checks: the RelaxNG row, the session row, the start row, and the two hand-off rows.
- **Grown:**
  - `cpython-a` → 275,176,000,396 (+2.45%);
  - `cpython-b` → 295,232,835,836;
  - `cpython-c` → 372,916,387,418.
- **Record:** `<scratch>/reviewer-delta-latest.json` (650 checks, `333d9bb`, `dirty: false`). **Log:** `<scratch>/judge-delta.log`.
- **Sameness** against the builder's `build/078/latest-full.json`: one difference. `cpython-a`'s fuel is 275,203,970,760 against 275,176,000,396, which is 1.016 × 10⁻⁴, past the 10⁻⁴ tolerance.
  - The two runs each side agree to within about 18,000 and 5,300.
  - The gap between the builder and me is about 28 M each time. So this is not random. Some host input reaches `cpython-a`'s fuel, as F9 said: the pre-083 file times and inode numbers.
  - **For the lane:** after the rebase onto 083, check that this gap closes. If it does not, sameness stops the landing on `cpython-a`, and that is a new cause for 083's author.

## Findings

### D1 (fix before landing): the `--accept-judge` text breaks in a shell

- **The fault.** The text is a double-quoted argument that contains `"No module named '_testcapi'"`. Pasted as written, the inner `"` ends the string at `widened to `, and `module`, `named` and the rest become stray arguments to pytest.
- **Fix:**
  - write the match with single quotes or none, for example: `match widened to No module named '_testcapi' (139 members)`;
  - say "two gaps' digests restated and one added";
  - add back "one comment in test_v1_4_embedding.py".

### D2 (note): the start row's "seen failing first" line does not reproduce

- `build-evidence/f1-start-interrupted.log` says the row, on `7aa0c52`'s runner, ended with "exit −6, no output".
- With the committed row (whose `close` stand-in only records), I get exit 0 with `bad closes ['MainThread', 'MainThread']` in four of four runs. That still fails the row's assertion.
- The −6 probably came from a version of the row that really closed the store.
- **Fix:** correct the line, or say which version of the row gave −6.

### D3 (note): the handshake's double-fault edges

- `_join_guest` now trusts only `ended`. There are two ways for it to wait for good:
  - **a second async exception in `_start_guest`'s `except`,** before it takes the lock, after a start that never made a thread: the state stays `starting` and nobody sets `ended`;
  - **an embedder's `threading.settrace` hook that raises** at the body's first frame: the body never runs and never sets `ended`.
- Both are exotic (INFERRED; not run).
- **A cheap backstop:** in the join loop, if `home.thread` was started (it has an ident) and is no longer alive while `ended` is unset, cancel under the lock and return.

## Verdict

The fixes are correct, and F1's handshake holds on every ordinary path. The judge reproduces the builder's verdicts, and the only sameness difference is the pre-083 fuel wobble, which the lane handles at the rebase.

**Lands once D1 is fixed.** It is a `context/` text edit. D2 and D3 are notes.

One line: the answers fix F1 (verified with my own probe, unchanged) and F2 to F11, and the judge agrees; only the `--accept-judge` text's nested quotes need fixing before landing.

## On the rebase onto 089 and 083

- **Under review:** `e145f6c`, the lane's rebase of 078 onto `45b917c` (the accepted batch of 089 and 083), with one more commit on top answering D1 to D3.
- **How I ran it:** the full judge on `e145f6c`, clean, the private set (one link per file), started with no `lane.lock`; then the three CPython groups once more by node id.

### The merge (READ)

- **The range-diff.** `git range-diff 3866f56..333d9bb 45b917c..83e6949` shows:
  - every 078 commit unchanged, except two context moves:
    - `7aa0c52` → `b242ac7`: `tests/harness/guest.py` gains main's `litter` import, and 083's `files.bind` line now sits inside the moved block;
    - `2a0a98d` → `b9b6d2f`: the roadmap hunk sits beside 089 and 090's entries; both blocks are kept.
- **`guest.py` against `45b917c`.** 078's own hunks only: the constants, `engine()`, `on_own_stack`, `run()`'s `go()`, and `Turns._call`'s `go()`.
  - **083 in `go()`.** `files.bind` instantiates the two trampolines on the run's store and keeps their exports. It touches no thread-local, context variable or thread identity. wasmtime's stores are not tied to a thread. So binding on the judge's guest thread is safe, and it still happens before the guest runs.
  - **The shadows themselves** run on that same thread, inside wasm calls. `FileFacts` is touched from no other thread while the guest runs.
  - **089 at the tail.** `watch = litter.Watch(...)` is made before the run, on the caller's thread. `watch.after()` then `_release` in a `finally` run after `on_own_stack` has joined, so after the guest thread has ended. That is the order 089 needs: the watch sees the run's own stdlib copy, and the release comes after.
  - **The `except BaseException: _release; raise` path** is main's, unchanged. `on_own_stack` re-raises the thread's exception only after its join.
- **`Turns`.** 083 does not shadow `Turns`, and 089 changes only its `close` (`_release`). 078's `_call` wraps `_initialize` and each export call in `on_own_stack`.
  - `Turns.__init__`'s instantiation still runs on the caller's thread, as it did at `7aa0c52`. That differs from the spec's "each `Turns` instance's calls (its instantiation included)", which I missed in the build review. A reactor's instantiation runs no guest function, so it is harmless.
  - **Fix:** a word in the spec, "its `_initialize` included", or wrap the instantiation too.

### The D1 to D3 commit (READ)

- **D1.** The `--accept-judge` text is one argument in a code block with no double quote inside. Its apostrophes sit safely inside the double quotes. It names "two gaps' digests restated and one added" and the embedding comment. Fixed.
- **D2.** The evidence line is corrected.
- **D3.** `_join_guest` adds a backstop: if `ended` is unset and the thread is gone, it cancels under the lock and returns.
  - **Sound.** `is_alive()` is false for a made-but-unstarted thread. But a body that has reached `running` implies `_started` is set, so a running guest is never cancelled.
  - A body that starts after the cancel returns at once.
  - The normal end sets `ended` before the thread exits. So the backstop fires only on the two double-fault paths.
  - A new unit covers it.

### The judge on `e145f6c` (EXECUTED)

`uv run pytest -n 3`, clean, with the machine under heavy load (load average about 224):

- `wasi_python v1: 543/656 pass · 57 gap · 56 blocked · 0 fail (unit suite 1624/1632, 8 skipped)`.
- `2167 passed, 64 skipped, 57 xfailed in 776.62s`.
- `ratchet vs 69004e2129: lost 0 · absent 14 · unrun locally 42 · gained 40 · grew 3 · more 3`.
  - The 14 absent are the retirements; the 40 gained are 078's checks.
- **Record:** `<scratch>/reviewer-rebased-latest.json` (656 checks, `e145f6c`, `dirty: false`). **Log:** `<scratch>/judge-rebased.log`.
- I put the same file back as the worktree's `build/progress/latest.json` after my node-id re-run, which had overwritten it.

### F9: does the `cpython-a` gap close on 083's base? Yes (EXECUTED)

- **`cpython-fs`** is 59,778,645,587, 083's deterministic value to the instruction.
- **The re-run.** I ran the three groups again by node id. Each gives the same fuel as the full judge, to the instruction (difference 0):
  - `cpython-a` 275,224,460,221;
  - `cpython-b` 295,386,337,705;
  - `cpython-c` 372,589,716,321. (`<scratch>/cpython-rerun.log`, `cpython-rerun-latest.json`.)
- Before 083, my runs and the builder's differed by about 28 M on `cpython-a`. On 083's base my repeat is exact. So the host input is gone, and I expect the lane's serial run to match within the tolerance (INFERRED for the lane's machine and the serial schedule).

### R1 (fix before landing): the growth text's percentages are stale on this base

- Against `69004e2`'s accepted values:
  - `cpython-a` 268,543,454,014 → 275,224,460,221: **+2.49%**;
  - `cpython-b` 294,423,867,726 → 295,386,337,705: **+0.33%**;
  - `cpython-c` 372,384,327,035 → 372,589,716,321: **+0.055%**.
- The `--accept-growth` text still says +2.5%, +0.24% and +0.12%. `cpython-b`'s and `cpython-c`'s numbers are now wrong: the same nine tests cost different fuel under 083's driver.
- **Fix:** restate the three percentages from the lane's own serial run before accepting. The numbers above are what I expect it to give.

### Verdict on the rebase

The merge composes correctly:

- the guest's wasm, 083's binding and its shadows run on the judge's guest thread;
- 089's watch and release run on the caller's thread, after the join, in 089's order;
- `Turns` is unaffected but for a word in the spec.

D1 to D3 are fixed, the judge is green with the expected moves, and the CPython groups' fuel now repeats exactly.

**Lands once R1 is fixed** (the growth text's percentages, from the lane's run). The `Turns` wording is a note.

One line: the rebase onto 089 and 083 composes cleanly, F9's wobble is gone (exact repeat), and only the `--accept-growth` percentages need restating on this base.
