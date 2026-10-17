# Review of 011 — The concurrency check's trap kind, after a start-up deadline

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution (§4, §7), `context/reviews/README.md` and the 014 build review (for its format).
  Then I read specification 011, the diff, and the runner's output, deadline and door paths. I
  was given the author's diagnosis and claims; I checked each one and did not rely on them. Each
  claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** the uncommitted change to `tests/checks/test_v1_4_embedding.py` (14 lines) on top
  of `6634dee`: the `trap` branch of the `CONCURRENT` script, and the docstring of
  `test_concurrent_calls_get_their_own_results`. It is a judge change.
- **Why it was made.** The pre-release dry run (GitHub Actions run 39030915226, job
  `verify (windows-2025)`) failed this check with `800 calls, 1 wrong, 0 raised`. The wrong call
  was `trap: Completed(exit_code=None, stdout=b'', stderr=b'', trapped='deadline', ...)`
  (EXECUTED: `gh run view 39030915226 --job 117393573782 --log`, lines 281-341). The other 85
  checks in that job passed; ubuntu-24.04 and macos-15 passed.
- **Re-ran (EXECUTED, darwin-arm64, Python 3.14.2, wasmtime-py 49.0.0).** Scripts and the
  Windows log are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/`
  (`variants.py`, `sync_probe.py`, `old_check.py`, `win.log`).
  - `uv run pytest tests/checks/test_v1_4_embedding.py -k concurrent -p no:cacheprovider` →
    `2 passed, 46 deselected`; ratchet `lost 0 · ... · judge changed: tests/.DS_Store,
    tests/checks/.DS_Store, tests/checks/test_v1_4_embedding.py` (see finding 3).
  - `uv run ruff check` and `uv run ruff format --check` on the file → clean.
  - `variants.py` takes the `CONCURRENT` string from a test file, applies one substitution, and
    runs it in a child process, as the check does. Results:

    | variant | summary |
    | --- | --- |
    | the change as it is | `800 calls, 0 wrong, 0 raised` |
    | the change, trap counts recorded | `trap calls 160, door reached 160` · `0 wrong` |
    | the change, `deadline_s=0.01` (two runs) | `door reached 95, stdout empty 56` · `0 wrong`; `door reached 103, stdout empty 48` · `0 wrong` |
    | HEAD's check, `deadline_s=0.01` | `800 calls, 45 wrong, 0 raised`, each `stdout=b'', stderr=b'', trapped='deadline'` |
    | HEAD's check as it is | `800 calls, 0 wrong, 0 raised` |
    | the change, guest prints another call's token | `160 wrong` |
    | the change, guest prints its token to stderr (own stdout lost) | `160 wrong` |
    | the change, guest exits 3 after the door instead of looping | `160 wrong` (`exit_code=3, trapped=None`) |

    At `0.01` s, 160 − 95 − 56 = 9 calls printed but did not reach the door. So both allowed
    outcomes of the no-door branch (`b''` and the token) occur, and the check accepts both.
  - I did not modify the repo. The only tracked-tree file I wrote is this review. While I
    worked, the 015 specification and its review changed in the tree; another piece of work
    owns them, and I ignored them.

## The questions asked, against evidence

1. **Is the diagnosis right? (READ, EXECUTED, INFERRED.)** Yes.
   - READ: `_instance` sets the epoch deadline at `runner.py:421-422`, before the stream set-up,
     `mkdtemp`, the stdin file, `store.set_wasi`, `_linker` (which takes `_lock`, the lock the
     ticker takes every round) and `linker.instantiate` in `_drive`. So `deadline_s` covers
     start-up. The ticker counts wall time, and other trap calls keep it running, so those ticks
     pass while this call is still setting up.
   - READ: the comment at `runner.py:414-417` says wasmtime fills memory per byte at
     instantiation on Windows always. That is start-up work that grows with load on a 4-core
     runner with 8 threads, and an epoch check fires at the first wasm function entry after.
   - EXECUTED: HEAD's check with `deadline_s=0.01` gives exactly the CI shape (`stdout=b''`,
     `stderr=b''`, `trapped='deadline'`), 45 times. `stderr=b''` also fits: a guest stopped
     before its print writes nothing anywhere.
   - **Could `b''` be a spec 011 defect instead? (READ.)** I looked for a way a flushed print can
     be lost.
     - `_send_outputs` registers both keys under `_outputs_lock` before `store.set_wasi`
       (`runner.py:642-650`). Keys come from a counter and are never reused.
     - `_output_write` looks the key up under the lock and writes into that call's own
       `_Stream`. If the key is gone it drops the bytes and reports success
       (`runner.py:627-634`). So a write after the key is popped would be lost silently.
     - Keys are popped only in `_instance`'s `finally`, after `store.close()`, so after the guest
       has ended (`runner.py:458-460`), and by `_output_free` when wasmtime drops the stream.
     - `_Call.stop` (`runner.py:538-545`) sets the epoch deadline of `caller._context()`, the
       store that is calling, never another. A stop records its cause in `call.stopped`, and
       `_drive` reports that cause, not `"deadline"`, unless the cause was itself an interrupt.
     So the only path to a lost own print is a write that reaches `_output_write` after the guest
     has ended. That needs `fd_write` to return before the callback has run.
   - **Does `print(flush=True)` reach the callback before the door call? (EXECUTED, INFERRED.)**
     `sync_probe.py` captures each call's stdout `_Stream` and reads it from inside the host
     function. In 20 of 20 calls the door saw `b"t-i\n"` already in the stream. Each print came
     as one write (`[b't-0\n']`): token and newline together, since stdout is a buffered writer
     and `BASE_ENV` sets no `PYTHONUNBUFFERED`. INFERRED: wasmtime's preview1 `fd_write` on stdio
     is a blocking write-and-flush, which waits for the custom stream's callback; the probe
     agrees on macOS, and the code path is the same on Windows.
   - So: once the door is reached, the token is in the stream, and losing it would be a real
     defect. Before the door is reached, `b''` means the guest had not printed. The author's
     reading of the CI failure is right.
2. **Does the new logic weaken what the check catches? (READ, EXECUTED.)**
   - Own output lost after the door: caught (the stderr variant, 160 wrong).
   - Foreign output: always caught, door or not, since the allowed set holds only `b''` and the
     call's own token (the foreign-token variant, 160 wrong). A partial or appended token is
     not in the set either.
   - A result other than a deadline trap: caught by `r.trapped != "deadline"` (the exit variant,
     160 wrong). A stop recorded by `_shared` reports its own cause, so it shows as something
     other than `"deadline"` or raises.
   - `printed.append(1) or b""` returns `b""`: `append` returns `None`, and `None or b""` is
     `b""`. READ `recipes/hostmodule.c:27`: `host_alloc(0)` is `malloc(1)`, never null, so the
     door answers 0 and `_host.call` returns `b""`. If it ever answered −2, the guest would raise
     `OSError` and exit 1, which the check flags; that failure is loud, not masked.
   - `printed` is local to each `one()` call, so threads never share it. A door call routed to
     the wrong call is caught by the `door` kind, as before.
   - **What it gives up.** Only one thing: a trap call that did not reach the door may now end
     with `b''`. HEAD treated that as wrong; it was wrong only if start-up fits in 0.2 s, which is
     a timing assumption (§4.9). The other 640 calls still demand their exact token. See
     finding 2 for what this can hide.
   - **The mix.** Trap calls now also bind a host and make one door call before they spin. The
     `door` kind already runs that path 160 times; this adds 160 more door calls under the same
     contention, and every trap call now has a `_door(host)` closure instead of `NO_HOST`.
     No kind used the no-host door before either. Nothing exercised before is lost.
3. **Remaining timing assumptions (READ).**
   - The trap branch has none left: the allowed set depends only on whether the door ran.
   - The `print`, `door`, `sleep` and `fuel` kinds run under the default 60 s deadline. Each
     assumes start-up (and, for `sleep`, a 0.01 s wait) finishes in 60 s. That is a fail-safe of
     the same kind as the documented 120 s child timeout, about 300 times the 0.2 s that just
     failed. It is not stated (finding 4).
   - The `time.sleep(0.01)` itself is not timed; nothing asserts how long it took.
   - Elsewhere with `deadline_s=0.2` (`test_v1_2_hostile_guest.py:321`, `:374`): those checks
     assert only `trapped == "deadline"` and `stdout == b''`, which hold even when start-up eats
     the whole deadline. They carry no such assumption.
4. **The run (EXECUTED).** Done above: the check passes; both of the author's variants
   reproduce (`0 wrong` at `0.01` s; `160 wrong` for another call's token).

## Findings, most severe first

1. **Specification 011 still describes the old check**
   (`context/specifications/011-concurrent-calls-share-nothing.md:189-193`). Low.
   - It says "a token printed before a deadline trap" and "every call must return its own token,
     with its own trap where one is expected". The changed check no longer demands a token from
     a trap call that did not reach its door. The spec also says 8 × 40 calls; the check has made
     8 × 100 since it landed.
   - **Fix.** Add a dated note to spec 011's checks section or its landing notes: the trap kind
     calls the door after its print, and must show its own token only once the door ran,
     because the deadline also covers start-up (Windows CI, run 39030915226). Cite this review.
2. **The trap kind's own-output guard can thin out on a loaded host, and nothing says how
   much** (`tests/checks/test_v1_4_embedding.py:423-430`). Low.
   - On this Mac, 160 of 160 trap calls reached the door at 0.2 s (EXECUTED). On a loaded
     runner, fewer will, and the check does not say how many did.
   - INFERRED: a defect that makes a deadline fire far too early (say, at instantiation) would
     now pass this check: 160 calls with `b''`. HEAD would have caught it, though only by its
     timing assumption. Such a defect is a deadline property, and §4.9 puts "too early" in a
     benchmark, not a test. A stop or a lost write still fails the other 640 calls or the
     door-reached trap calls.
   - **Fix (optional).** Print a second, unasserted line in the child, such as
     `trap calls reaching the door: N/160`, so a failure log or a curious reader can see the
     coverage. Do not assert a minimum: that would be a timing assumption again.
3. **The judge hash on this machine includes Finder files** (`tests/harness/paths.py:114-128`).
   Low, for the landing.
   - EXECUTED: the ratchet reports `judge changed: tests/.DS_Store, tests/checks/.DS_Store, ...`.
     Both files are ignored by the user's global gitignore and are not in `git ls-files`.
     `judge_files` walks `JUDGE_PATHS` with `rglob`, so it hashes them.
   - INFERRED: an `--accept-judge` run on this machine records a judge hash that a clean clone or
     CI cannot reproduce.
   - **Fix.** Delete the two `.DS_Store` files before the acceptance run. Making `judge_files`
     skip untracked files is a judge change of its own, with its own reason; not for this diff.
4. **The 60 s default deadline on the other four kinds is an unstated fail-safe**
   (`tests/checks/test_v1_4_embedding.py:409-422`, the docstring at `:457-463`). Info.
   - The docstring names the 120 s child timeout as a fail-safe, not a timing. The 60 s default
     deadline on 640 calls plays the same role. Passing `deadline_s=None` would remove it, but
     would also stop those calls from running the ticker and spec 010's sliced waits under
     contention, which is part of what the check exercises.
   - **Fix (optional).** One clause in the docstring: "the other calls keep the default 60 s
     deadline, a fail-safe like the timeout."

## Constitution checks

- **§4.9, tests count.** The change removes a timing assumption (start-up under 0.2 s) and adds
  none. The trap branch's verdict depends only on whether a host call happened.
- **Never weaken the judge (AGENTS.md rule 4).** This is a judge change with a stated reason: the
  CI log above. It is not a loosening to get a pass on a real defect: the diagnosis holds
  (question 1), and every defect class the check targets is still caught (question 2), with the
  one gap in finding 2. It needs `--accept-judge "<reason>"` at acceptance.
- **§4.4, the door.** The guest uses the existing door; no import is added.
- **§4.5, embedder-neutral.** Holds.
- **§4.10, claims carry evidence.** The new comment and docstring claim nothing they do not
  show. The spec text does not yet match (finding 1).
- **§7.** Nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — Fixed: spec 011's check section gains a dated note (8 × 100, the door witness,
   the dry run, this review).
2. Finding 2 — Taken: the child prints "trap calls that reached the door: N of 160", not
   asserted, and the test passes it through to its output. EXECUTED here: 160 of 160.
3. Finding 3 — Fixed in the harness: deleting the files did not hold (Finder recreated them,
   and history line 18 records them), so `judge_files` now skips `OS_LITTER` (`.DS_Store`,
   `Thumbs.db`, `desktop.ini`), with `test_files_an_os_writes_are_not_part_of_the_judge`.
   Line 18 stays; line 19 records the judge without them.
4. Finding 4 — Taken: the docstring names the 60 s default deadline as a fail-safe.

## Verdict

Lands, once finding 1 is answered and the acceptance run is recorded with `--accept-judge`
after finding 3's clean-up. The diagnosis is right: the deadline covers start-up, and the CI
failure's shape reproduces exactly with a short deadline. A flushed print reaches its stream
before the door call, so the door is a sound, timing-free witness. The new branch still catches
lost own output once the print ran, foreign output always, and any result other than a deadline
trap.

One line: the change swaps a hidden start-up timing assumption for a host-call witness, and still
catches every wrong result the trap kind was there to catch.

## Confirmation, 2026-10-17

The same reviewer. I read `git diff tests/ context/specifications/011-concurrent-calls-share-nothing.md`,
the dispositions above, `context/progress/README.md`, the uncommitted `history.jsonl` line 18
and `scoreboard.history_errors`. The scripts are in the same scratch directory
(`litter_mut.py`, `fast.txt`).

- **Re-ran (EXECUTED).** `uv run pytest -m "not slow" -p no:cacheprovider` → `140/146 pass ·
  0 gap · 2 blocked · 0 fail` (unit suite 302/302), `442 passed, 2 skipped`, exit 0; ratchet
  `lost 0 · ... · judge changed: tests/.DS_Store, tests/checks/.DS_Store, tests/harness/paths.py
  and 1 more`. Both `.DS_Store` files were back in the tree when I ran. `ruff check` and
  `ruff format --check` on `src tests` are clean. The concurrency check with `-s` prints
  `trap calls that reached the door: 160 of 160` and passes.

1. **Finding 1 — confirmed, with one wording nit.** The note is in spec 011's checks section and
   cites this review. It says "8 × 40 was flaky". The check's own comment says something
   different: 8 × 40 caught the *old runner's defect* in only 2 of 3 runs. "Flaky" reads as if
   the check failed on correct code. Suggested: "8 × 40 caught the defect in only 2 of 3 runs".
   Not a blocker.
2. **Finding 2 — confirmed.** READ: `reached` gets one entry per trap call whose door ran; the
   line is printed last, so it also shows in the assertion's `out.stdout[-2000:]` when the check
   fails. `THREADS * CALLS // 5` is exactly the number of trap calls (each thread's 100 calls
   rotate through 5 kinds). Nothing asserts it.
3. **Finding 3 — confirmed, by the harness fix, not by the disposition as written.** The
   disposition text still says the files were deleted; it should say the deletion did not hold
   and `OS_LITTER` replaced it.
   - **The filter is sound (READ).** It drops a file by its exact name: `.DS_Store`,
     `Thumbs.db`, `desktop.ini`. None of these can steer pytest: they are not `.py`, not
     `conftest.py`, not an ini file pytest reads. The stray-`conftest.py` walk is untouched.
     Using `git ls-files` instead would be wrong: a new check is a judging file before it is
     added to git.
   - **The test (EXECUTED, `litter_mut.py`).** Removing the filter line fails it, and restoring
     the line passes it, as the author saw. But emptying `OS_LITTER`, or dropping `.DS_Store`
     from it, still passes: the test writes only the names in the set, so it shrinks with the
     set. Fix (small): have the test also write a literal `.DS_Store` (and check that it is
     in `paths.OS_LITTER`). Not a blocker.
   - Info: macOS also writes `._*` AppleDouble files on non-HFS volumes. Leave them out until
     one is seen.
4. **Finding 4 — confirmed.** The docstring names the 60 s default deadline as a fail-safe.

**Line 18: leave it, and append line 19.**
- `context/progress/README.md`: the two files are "written only by `uv run pytest --accept`,
  never by hand", and the history is append-only. Removing line 18 means rolling
  `accepted.json` back as well, since the last history line must hash it. That is either a hand
  edit, or a `git restore` of a file with uncommitted work, which AGENTS.md forbids.
- INFERRED from `history_errors`: the integrity check would pass either way. It compares
  against the committed history, and line 18 is not committed yet. So the rule decides this, not
  the tool. The rule says append.
- Line 18 is a true record. The run was green, and its `judge_changed` names the litter
  honestly. Line 19 will show the two files leaving the judge, together with `paths.py` and
  `test_scoreboard.py`, under its own `--accept-judge` reason. Anyone reading the history then
  sees what happened and why. That is the history's purpose.
- The one cost: CI cannot reproduce line 18's judge hash. Nothing checks an old line's judge
  hash; only `accepted.json`, which line 19 rewrites, is compared. So it costs nothing.
- For line 19's reason, name both changes: the concurrency check's door witness, and
  `OS_LITTER` (this review, finding 3).

**Verdict (confirmation).** Lands. Before or with the commit, update finding 3's disposition text
to match what was done. Then record line 19 with `--accept-judge`, leaving line 18 as it is. The
nits in 1 and 3 (the "flaky" wording and a literal `.DS_Store` in the test) are worth taking but
do not hold the landing.
