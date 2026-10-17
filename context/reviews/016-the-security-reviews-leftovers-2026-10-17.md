# Review of 016 — The security review's leftovers (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution (§4, especially §4.9 and §4.15; §5.6; §7), `context/reviews/README.md` and the 015
  build review (for its format). Then I read specification 016 with its landing notes, its
  pre-build review with both confirmations, and the diff. I did not rely on the landing notes.
  Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** the scratch clone's `git diff 9ed86d6 HEAD` (one commit, `47fc480`):
  `src/wasi_python/runner.py`, `.github/workflows/release.yml`, `tests/checks/test_v1_2_hostile_guest.py`,
  `tests/checks/test_v1_4_embedding.py`, the new `tests/unit/test_runner_sweep.py`, `README.md`,
  `CHANGELOG.md` and the specification.
- **Re-ran (EXECUTED, darwin-arm64, 10 cores, CPython 3.14.2, wasmtime-py 49.0.0, the main tree's
  `build/artifacts` read only, `WASI_PYTHON_CACHE` the main tree's `build/cwasm-cache`).** Probes,
  outputs and logs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev016b/`
  (`pytest-full.txt`, `repeat.txt`, `probes/*.py` with their `.txt`, `mut/mutations.txt`,
  `mut/standins-rerun.txt`, `mut/*/log.txt`, `wheel-mac.txt`, `wheel-linux.txt`, `fix/`).
  - `uv run pytest -p no:cacheprovider` in the clone → `155/166 pass · 0 gap · 11 blocked · 0 fail
    (unit suite 331/337, 6 skipped)`; v1.4 `59/59`; `486 passed, 17 skipped`; ratchet vs
    `1abb07264f`: `lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 3 · grew 0 · judge
    changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py,
    tests/unit/test_runner_sweep.py`; `next: context/research/2026-10-16-reproducible-builds-on-linux.md
    (unblocks 7, closes 0)`; **exit 0**. The 11 blocked are the clone's missing source trees,
    oracle, prior-art clones, three systems and wheel. I did not pass `--accept`.
  - `ruff check src tests` → all checks passed; `ruff format --check src tests` → 47 files
    already formatted.
  - The new and changed checks (the sweep unit file, the stack-overflow check, the descriptor
    check, the two v1.4 sweep checks; 23 tests), five times idle and three times under 20 busy
    shell loops: `23 passed` every time.
  - **How I probed and mutated.** I never edited the clone. Probes run the clone's own runner in
    real processes; pauses are injected by wrapping a function in the probe's own process. Each
    mutation went into its own copy of `src/` (`rev016b/mut/<name>/`), run from a `git archive`
    copy of the clone with `PYTHONPATH` set to the copy; four mutations being caught shows the
    copy was the code under test. At the end the clone's index matched the list I took first,
    and `git diff` was empty.
  - I did not commit, push, run `scripts/build.sh` or touch `build/artifacts/`. My judge run
    rewrote untracked state under the clone's `build/`. I pulled `python:3.13-slim`'s existing
    image only; inside a throwaway container I downloaded uv 0.9.22 and the pinned hatchling to
    build one wheel. The only file I wrote outside `rev016b/` is this review.

## Decisions against the code

- **Decision 3, trap names (READ, EXECUTED).** `_trap_name` (`runner.py:1349`) keeps
  `"out of fuel"` and `"deadline"`, then names any other coded trap by
  `code.name.lower().replace("_", " ")`, then falls back to the first line. The v1.2 check gives
  `trapped == "stack overflow"`. The old-name stand-in fails both new checks (EXECUTED). The
  CHANGELOG says plainly that this is "a change to what it says" and quotes the old heading, and
  the README lists the kinds. That is honest. A stale comment remains (finding 9).
- **Decision 4, the Windows cache sentence (READ).** Present in the cache paragraph, as specified.
- **Decision 1, the wheel (READ, EXECUTED).** See "The workflow" below.
- **Decision 2, the private folders and the sweep.** See the next three sections.

## 1. `_Private`: the creation order, redraw, abandon and remove

- **The order is Decision 2's (READ, `runner.py:481-515`).** The name joins `_held` under
  `_held_lock` first. Then `os.open` with `O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC|O_BINARY`
  and mode 0600. Then `_try_lock`. Then `_same_file` (fstat against lstat, device and inode).
  Then, if there is an identity, `lseek(0)` and one `write`. Then `os.mkdir(path, 0o700)`.
- **Redraw.** `FileExistsError` from the open drops the name and redraws. `_Taken` (busy lock or
  not the same file) and `FileExistsError` from `mkdir` go to `_abandon` and redraw. Anything
  else goes to `_abandon` and re-raises. After 100 draws it raises `FileExistsError`, as
  `mkdtemp` does.
- **Abandon (READ).** It closes the fd, unlinks the lock file only if `held`, then drops the
  name. Two gaps:
  - `_same_file` calls `os.lstat`, which raises `FileNotFoundError` when a sweeper has just
    removed the new file. That is not `_Taken`, so it re-raises (finding 1, EXECUTED).
  - When `_same_file` is false, `held` is still true, so `_abandon` unlinks whatever now has that
    name. The spec says "removes only a lock file this call created and still holds". With
    64 random bits a different file there is not a practical case, but the code does not do
    what the spec says (finding 1's fix covers it).
- **Remove (READ, EXECUTED).** `rmtree(ignore_errors=True)`, `close` (errors ignored), unlink only
  if `lexists(path)` is false (errors ignored), then `_drop` last. Nothing in it can raise but a
  `KeyboardInterrupt`. EXECUTED (`probes/stepped.txt`, p5): a call paused between its close and
  its unlink while another process swept: the sweeper took the lock, found no folder, removed the
  lone lock file; the call then resumed, its unlink failed quietly, and nothing was left. p5b: a
  folder `rmtree` could not fully remove kept its lock file, and the sweeper (which could not
  remove it either) left both.
- **File descriptors (READ).** The creator's fd lives until `remove()`; both callers call
  `remove()` in a `finally`. `_sweep_entry` closes its fd in a `finally`. No leak found. But if
  `_Private` raises inside `_instance` (`runner.py:834`), it is outside the `try`, so
  `store.close()` and the `_outputs` clean-up are skipped. That ordering is old (it was `mkdtemp`),
  but `_Private` now raises in more cases (findings 1 and 2).

## 2. `_sweep_entry`: order, races, and whose folders it can touch

- **Order (READ, `runner.py:577-611`).** Name pattern; not held; `lstat` regular and owned;
  `open(O_RDWR|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC|O_BINARY)`; `fstat` regular with `lstat`'s device and
  inode; `_try_lock`; read the first line from offset 0; with no folder, unlink only if the line
  is empty or this kernel's identity; else the identity must match; the folder must be a
  directory and not a junction; `rmtree`; count it if gone; close; unlink if the count happened
  or the lone rule allowed it. It matches Decision 2.
- **A live call's folder is never removed (EXECUTED).** I found no path that removes one.
  - Two or more sweepers at once (`probes/p3.txt`): 10 rounds, each with 200 dead folders, 20 live
    folders held by a third process, and four sweeper processes released together. Each round the
    four counts summed to exactly 200, all 40 live entries stayed, and the holder found its data
    intact and cleaned up after itself.
  - Creators and sweepers at full speed (`probes/p4.txt`): two processes made and removed 3,000
    private folders each while four processes swept 300 times each. No live folder lost its
    data (`lost 0`). But 5 of the 6,000 creations raised `FileNotFoundError` (finding 1).
  - A call that ends while a sweeper holds its lock (`stepped.txt`, p5, above): correct.
  - A sweeper that closes, then the creator locks and makes its folder, then the sweeper unlinks
    (`stepped.txt`, p2): the live call's **lock file** is removed, its folder is kept. A later
    sweeper leaves the folder (no lock file). The call cleans up normally. That is a leak if the
    call is then killed, never a removal (finding 6).
- **Another user's (READ, INFERRED).** The lock file must be this user's (`st_uid`), a regular
  file, not a link. The folder's owner is not checked. A folder another user puts beside one of
  our lone lock files gets `rmtree`d as us, which can delete only what that user let us delete,
  and `rmtree` does not follow links (fd-based here). INFERRED: no harm. But the owner check
  itself is not tested (finding 4).
- **Another kernel's (EXECUTED).** The identity stand-in fails both kernel cases. A lone lock
  file naming another kernel stays (`test_a_lone_lock_file[another-False]`; m06 caught).
- **The lone-lock rule.** A lone lock file whose lock is free and whose first line is this
  kernel's identity belongs to a dead creator or to a call between its close and its unlink.
  Both are safe to remove. An empty one also belongs to a live creator between `O_EXCL` and its
  lock. Removing it is what opens findings 1 and 6. The fix for finding 1 makes that creator redraw.
- **`O_NONBLOCK` (EXECUTED).** It is there, but the FIFO check cannot see it: without it the check
  still passes and does not hang (m02), because `O_RDWR` on a FIFO does not block on macOS (nor,
  INFERRED, on Linux). The fstat and inode checks are what skip the FIFO. `O_NONBLOCK` still
  matters for a Linux file under a lease (INFERRED). See finding 8.

## 3. Windows (nothing here was run; every Windows claim is READ or INFERRED)

- **`O_BINARY` is right and needed (INFERRED).** Without it the C runtime's text mode writes the
  identity's `\n` as `\r\n`. The sweeper's first line would then end in `\r` and never equal the
  identity, so nothing would ever be swept.
- **`msvcrt.locking` does not need a non-empty file (INFERRED).** `LockFileEx` allows a range
  past the end of the file. The creator locks byte 0 of an empty file, then writes into it
  through the same handle, which the lock allows.
- **The `lseek` before locking is right (INFERRED).** `_locking` locks from the current position.
  From memory of the UCRT source, it does not move the pointer, and `_sweep_entry` seeks to 0
  before reading anyway. `LK_NBLCK` makes one attempt, and a failure is an `OSError`, which
  `_try_lock` turns into `False`.
- **A Windows lock also blocks reads of its range, from any other handle, in the same process
  too (INFERRED, from the `LockFileEx` documentation; the pre-build review's C1 said the same).**
  The runner never reads a lock file it has not locked, so the runner is fine. But
  `test_a_private_folder_goes_before_its_lock_file` reads a held lock file with
  `Path.read_text()`, which should raise `PermissionError` on Windows (finding 3).
- **`_same_file` (READ, CPython 3.15's `Python/fileutils.c`; INFERRED for 3.14.2).** `fstat` and
  `lstat` both report the 64-bit volume serial and the 128-bit file id, so they agree on NTFS and
  ReFS. On a filesystem where `FileIdInfo` fails, `fstat` falls back to the 32-bit serial. If the
  by-name path does not, every creation would be `_Taken` (INFERRED, unlikely for a temporary
  folder).
- **`MachineGuid` with `KEY_WOW64_64KEY`** is read as specified (READ).
- **`_owned` is always true on Windows** (READ). It relies on `%TEMP%` being per user, as the spec
  decided.
- **The lock after a `close` (INFERRED, low).** Microsoft documents that the time to release the
  locks of a closed handle or a dead process "depends upon available system resources".
  `_locks_free` unlocks by closing, and child 2 then needs those locks. An explicit
  `msvcrt.locking(fd, LK_UNLCK, 1)` before `os.close` removes that doubt (finding 9).

## 4. The workflow (Decision 1)

- **Upload and download (READ).** `rebuild` builds the wheel after the set, with the build job's
  exact command, and uploads `dist/wasi_python-*.whl` as `rebuild-wheel-<os>`. `same-bytes`
  downloads it to `rebuilt-wheels/<os>/`. `write_assets` keeps the wheel's own name
  (`release/version.py:173-174`), so `$(basename "$wheel")` finds it. `same-bytes` has no `if:`,
  so a dry run runs it. The actions are pinned by the same commits as before.
- **The four rules (READ, EXECUTED by the author's `wheelcheck/`, which I read).**
  - Rule 1, `sha256sum --strict -c` in the wheel's artifacts folder against the set's sums, by
    absolute path: GNU `sha256sum` fails a missing file.
  - Rule 2, `cmp` of the two `SHA256SUMS`.
  - Rule 3, the listed names plus `SHA256SUMS` against `find -type f`. It does not see a symbolic
    link or an empty folder, but rule 4 does.
  - Rule 4, `cmp` of the whole wheel. Under the default `bash -e`, each failure stops the step.
  - The author's four altered copies each fail the intended rule.
- **Will the arm64 Linux wheel equal the macOS one? (EXECUTED, INFERRED.)**
  - EXECUTED (`wheel-mac.txt`, `wheel-linux.txt`): I built the same tree (`git archive` of the
    clone plus the main tree's set) twice. Once on macOS: uv 0.9.22, uv's CPython 3.14.2, zlib
    1.2.12. Once in a `linux/arm64` Debian container: uv 0.9.22 downloaded there, its CPython
    3.14.2, zlib 1.3.1, run as root with umask 022. Both used the pinned hatchling and
    `SOURCE_DATE_EPOCH=1767225600`. Both wheels hash **`d38dc37f…`**, byte for byte. So the
    interpreter, zlib and OS do not change the wheel.
  - READ (the pre-build confirmation, and `unzip -Z`): hatchling turns every mode into 644 or 755.
    Only the owner's execute bit survives. Every entry here is `-rw-r--r--`.
  - READ (`scripts/assemble_artifacts.py:129-192`): the set is written with
    `shutil.copyfile`, `write_bytes` and `write_text`. None sets an execute bit, on either OS.
    INFERRED: the two hosts' umasks cannot matter, because hatchling normalizes the group and
    other bits.
  - My build used one set copied on macOS. CI builds a separate set on each host, but `same-bytes`
    already proves those sets are byte-identical, and their modes come from the same script.
  - INFERRED: the CI wheels will be equal. The dry run's `same-bytes` log is the proof:
    `ubuntu-24.04-arm: the same wheel`. If they differ, `cmp` prints only a byte offset. Finding
    7 makes the failure name the entry.

## The checks

- **They count (READ).** Every new assertion is on exit codes, `trapped`, `_swept`, directory
  entries or file contents.
  - `_locks_free`'s `time.sleep(0.1)` paces up to 1,200 lock attempts. Its result is a boolean,
    asserted as a fail-safe, and on POSIX the first attempt succeeds. The 120 s `queue.get` and
    child timeouts are fail-safes too. None of them asserts a duration. §4.9 holds.
  - If Windows took more than 120 s to free a dead process's lock, the check would fail. That is
    a fail-safe, not a measured time.
- **Not flaky here (EXECUTED).** 5 idle runs and 3 under load: `23 passed` each time.
- **Each can fail (EXECUTED).** I re-ran the author's stand-ins in copies (`mut/standins-rerun.txt`):
  - the sweep ignores the lock → `test_a_held_lock_keeps_its_folder` and
    `test_a_live_calls_folders_are_never_swept` fail;
  - the sweep ignores the identity → both kernel cases fail;
  - no sweep → the killed-process check fails;
  - a busy lock raises → `test_a_busy_name_is_drawn_again` fails;
  - the old trap name → both trap checks fail.

  That matches the landing notes' table.
- **Mutations (EXECUTED, `mut/mutations.txt`, logs in `mut/<name>/log.txt`).** Each was run
  against the sweep unit file and the two v1.4 sweep checks.

| # | mutation | result |
|---|---|---|
| m01 | `_owned` always true | **survives** (finding 4) |
| m02 | no `O_NONBLOCK` in the sweep's open | **survives** (finding 8) |
| m03 | `remove()` unlinks the lock file even when the folder is left | **survives** (finding 5) |
| m04 | the sweep ignores the held set | caught: `test_a_name_this_process_holds_is_never_swept` |
| m05 | `remove()` drops the lock file before the folder | caught: `test_a_private_folder_goes_before_its_lock_file` |
| m06 | a lone lock file of any kernel is removed | caught: `test_a_lone_lock_file[another-False]` |
| m07 | no regular-file check after `open` | survives: the inode check still skips the FIFO |
| m08 | no inode check after `open` | survives: the regular-file check still skips the FIFO |
| m09 | `remove()` drops the name first | survives; only an NFS client could see it |
| m10 | no directory/junction check on the folder | survives: `rmtree` refuses a link (the author's note) |
| m11 | no regular-file check on `lstat` | survives: `O_NOFOLLOW` refuses the link |
| m12 | no identity written | caught: two checks |
| m13 | no `O_EXCL` | survives; no check names it (finding 8) |
| m14 | the name joins the held set after the open | survives; only an NFS client could see it |

m07, m08, m10 and m11 are layered defences: the outcome is guarded, and each layer alone is
not. That is acceptable, and the landing notes should say so, as they do for m10.

## Acceptance criteria against evidence

1. *The checks exist and were seen failing before the change.* **Met** for each property
   the landing notes name (stand-ins re-run). Partly weak: findings 4, 5 and 8.
2. *`uv run pytest` is green with `--accept-judge`.* **Met, pending the acceptance run.** EXECUTED:
   exit 0, `lost 0 · gained 3 · grew 0`, the judge changed in the three named files.
3. *A dry run of the release workflow passes every job.* **Not shown**, and INFERRED to fail on
   `verify (windows-2025)` (finding 3).

## Findings, most severe first

1. **A sweeper that removes a new, still-empty lock file makes the creator raise, and so `run`
   raises** (`runner.py:467-470`, `501`, `507-512`). Medium.
   - Decision 2 says a failure at step 3 ("a path that is no longer this file") draws a new name.
     But `_same_file` calls `os.lstat`, which raises `FileNotFoundError` when the path is gone. The
     `except BaseException` arm re-raises it.
   - Failure, EXECUTED (`probes/stepped.txt` p1, `probes/p1run.txt`):
     1. A creator is paused between its `O_EXCL` open and its lock.
     2. Another process's first call sweeps. It finds the lone, empty, unlocked lock file and
        removes it, as the lone-lock rule allows.
     3. The creator resumes: `wasi_python.run` raises
        `FileNotFoundError: … wasi-python-root-db402d8cef78071e.lock`.
   - With no pause (`probes/p4.txt`), 5 of 6,000 creations raised under continuous sweeping.
     Real sweeps are once per process start, so this is rare. But it is an exception out of `run`
     caused by another process, which the security review's F1 rule forbids. It also skips
     `store.close()` (section 1).
   - Fix: let `_same_file` return `False` on `OSError`, and set `held = _try_lock(fd) and
     _same_file(fd, lock_path)`. Then a creator that lost its file redraws, and `_abandon` unlinks
     only a file this call holds *and* that is still this file, as the spec says. EXECUTED in a
     copy (`fix/`, `probes/p1-fixed.txt`, `probes/p4-fixed.txt`): the paused creator redraws and
     succeeds, and the stress run makes 6,000 of 6,000 with 0 errors and 0 lost. Add a unit case:
     a fake `_try_lock` that unlinks the file before locking, and the call succeeds.
2. **On a temporary folder whose filesystem refuses locks, every call fails and leaves 100 lock
   files behind** (`runner.py:450-464`, `501-515`). Medium. A regression: `mkdtemp` worked there.
   - `_try_lock` turns every `OSError` into "busy". So `ENOLCK` (NFS without a lock daemon) and
     `ENOTSUP`/`EOPNOTSUPP` (some network filesystems) are treated like a held lock: `_Taken`, a
     redraw, and a lock file that `_abandon` leaves because it was not held.
   - Failure, EXECUTED with a fake `fcntl.flock` raising `ENOLCK` in the probe process only
     (`probes/enolck.txt`): `run` raises `FileExistsError: [Errno 17] no usable temporary folder
     name found`, and the temporary folder holds **100 empty lock files** from that one call.
   - INFERRED: which real filesystems do this is uncertain. The spec names `ENOLCK` for the sweep
     ("leaves the entry alone") but does not decide it for creation. That is a §5.2 gap the build
     filled silently.
   - Fix (a spec amendment, then code):
     - Treat only contention as busy: `BlockingIOError` (`EWOULDBLOCK`/`EAGAIN`) on POSIX, and
       `EACCES`/`EDEADLOCK` from `msvcrt.locking`.
     - On any other lock error, either:
       - go on without a lock and without writing the identity. A folder whose lock file has an
         empty first line is never swept, so this is a leak, never a removal; or
       - remove the lock file and raise a clear `OSError` at once.

       The spec chooses one and says why.
     - Add a unit case: a fake `flock` that raises `ENOLCK`, then a call. Either it succeeds, or
       it raises the chosen error and leaves no lock file.
3. **A new unit test reads a held lock file, which Windows refuses; the `verify (windows-2025)`
   job should fail** (`tests/unit/test_runner_sweep.py:174`). Medium (it blocks criterion 3, not
   the product).
   - `lock.read_text()` runs while `_Private` holds the lock on byte 0. A Windows exclusive lock
     denies reads of its range through any other handle, the same process's included
     (INFERRED, from the `LockFileEx` documentation).
   - Failure, INFERRED: `PermissionError: [Errno 13]` on windows-2025, which runs this file
     (`release.yml:230`).
   - Fix: read through the holder's own descriptor
     (`os.lseek(private.fd, 0, 0); os.read(private.fd, 100)`). Or move the identity check after
     the lock is released, or skip only that line on Windows. Or, as the pre-build review's C1
     suggested, have the runner lock a byte past the identity, so that a reader is never
     blocked. The dry run then shows the Windows path for the first time.
4. **The owner check is never exercised: the test replaces `_owned` itself**
   (`tests/unit/test_runner_sweep.py:104-107`). Low.
   - The spec says "an owner other than this user is refused, through a fake `lstat`". Replacing
     `_owned` with `lambda st: False` proves only that the sweep calls it.
   - Failure, EXECUTED (m01): `_owned` changed to `return True` passes every check. On a shared
     Linux `/tmp` this is the guard against sweeping another user's files. Locks and permissions
     would mostly stop that today (INFERRED), but nothing would notice the guard was gone.
   - Fix: fake `os.lstat` for the lock path only, returning a `stat_result` whose `st_uid` is
     `os.getuid() + 1` (POSIX), and assert that the folder stays. Also unit-test `_owned` on two
     `stat_result`s.
5. **The rule "a folder `rmtree` could not fully remove keeps its lock file" has no check**
   (`runner.py:525`). Low.
   - Failure, EXECUTED (m03): `remove()` unlinking the lock file always passes every check. What
     is left then has no lock file and is never swept: the guest's files leak for good.
   - Fix: a unit case with `runner.shutil.rmtree` made a no-op (or, on POSIX, a 0500 subfolder):
     after `remove()` the lock file is still there, unlocked. Then a sweep from a fresh claim
     removes both.
6. **A sweeper can unlink a live call's lock file** (`runner.py:601`, `606-611`). Low.
   - Failure, EXECUTED (`probes/stepped.txt`, p2):
     1. The sweeper locks a new, empty lone lock file, decides to unlink it, and closes.
     2. The creator then locks, passes `_same_file`, writes its identity and makes its folder.
     3. The sweeper unlinks the lock file.
   - Result: the live folder stays, but without a lock file. A later sweep leaves it (correct).
     If that call is then killed, its folder (and the caller's `stdin`) leaks for good: the F6
     outcome this specification fixes.
   - Fix (optional): on POSIX, have the sweeper unlink before it closes. A creator that then gets
     the lock fails `_same_file` and redraws, given finding 1's fix. Windows cannot unlink an
     open file, so there the window stays. Or record it in the landing notes as a known leak
     window.
7. **When `same-bytes` finds two different wheels, it says only where they differ, not which
   file** (`release.yml:190-193`). Low.
   - I found no cross-host difference (EXECUTED: the same `d38dc37f…` from macOS and arm64 Linux).
     But if the dry run differs, `cmp` prints a byte offset into a 38 MB zip.
   - Fix: before the `cmp`, print both wheels' entries with mode, size and CRC
     (`zipinfo -v`, or `python3 -m zipfile -l` plus `unzip -Z`) and `diff` them. Do it only on
     failure if you prefer.
8. **Some defences have no check that can see them** (`O_NONBLOCK`, `O_EXCL`, and the held set's
   order). Low.
   - EXECUTED: m02, m13 and m14 survive.
   - The FIFO check's name ("without hanging") claims more than it can show: `O_RDWR` on a FIFO
     never blocks on macOS.
   - Fix:
     - Say this in the landing notes, as they already do for the link case.
     - For `O_EXCL`, add a cheap unit case: fake `secrets.token_hex` to draw an existing name
       first, and assert the existing lock file is untouched and a second name is used.
9. **Small things.** Nit.
   - `runner.py:230`, `Completed.trapped`'s comment, still says "or the trap's first line". It
     also omits `"cancelled"`.
   - `test_a_failing_listing_leaves_the_call_alone` does not make a call, though the spec says
     "and the call goes on".
   - `_locks_free` releases its Windows locks by closing only. Add
     `msvcrt.locking(fd, LK_UNLCK, 1)` before the close, to remove the documented release delay.
     The same in `remove()` and `_sweep_entry` would hand locks on promptly.
   - The macOS `sysctlbyname` call has no `argtypes`. It works (EXECUTED: the identity reads)
     because libffi widens the trailing `0` to the 64-bit `size_t` (INFERRED). Setting `argtypes`
     makes that explicit.

## Constitution checks

- §4.1 (zero patches), §4.2 (pins), §4.3, §4.4: untouched. The two new action uses are pinned
  by the same commits as the existing ones (READ).
- §4.5 (embedder-neutral): nothing host-specific was added.
- §4.9 (tests count): holds. The sleeps and timeouts are fail-safes, and no duration is
  asserted (READ).
- §4.10 (claims carry evidence): the landing notes label their claims. The stand-in table matches
  my re-run.
- §4.13 (tooling): ruff clean. No dependency added.
- §4.15 (safe by default): no channel opens. The lock files sit outside the guest's root. The
  sweep removes only this user's files, from this kernel, with free locks, whose names this
  process does not hold. A `root=` at or above the temporary folder is named in the README as
  something never to grant. Finding 2 is a robustness regression, not a loosened default.
- §5.6: this change answers the 0.1.0a2 security review's F5, F6, F7 and F10. Findings 1 and 2
  put back an F1-style path: `run` raising because of the environment.
- §7: nothing tripped. I committed nothing.

## Disposition (filled in by the author, then confirmed by the reviewer)

Every finding is fixed in the clone as uncommitted changes on `47fc480`; the specification's
landing notes gain "Revised against the build review". EXECUTED in the clone with the main tree's
artifact set: `155/166 pass · 0 fail · 11 blocked`, unit suite 338/344, `493 passed, 17 skipped`,
ratchet `lost 0 · gained 3 · grew 0`; ruff clean. Mutations, probes and their output are under
scratch `build016/mut2/`.

1. **Fixed as suggested.** `_same_file` returns False on `OSError`. The creator sets `owns` from
   step 3 and `_abandon` unlinks only when `owns`, so a file no longer this call's is never
   removed. New unit case `test_a_lock_file_swept_before_its_lock_makes_the_creator_draw_again`
   (a `_try_lock` that unlinks the file first). Your probes, re-run against the fixed clone
   (`mut2/probes/stepped2.txt`): p1 draws again and succeeds; p1run runs; p4 makes 6,000 of
   6,000 with `errors {}` and `lost 0`.
2. **Fixed by a spec decision: go on without a lock and without an identity.** Decision 2 gains
   "A filesystem without locks", which says why: a leak is the behaviour before this
   specification, while raising would make every call fail where `mkdtemp` worked. `_try_lock`
   now answers `True`, `False` (contention only: `BlockingIOError` on POSIX, `EACCES`/`EDEADLOCK`
   on Windows) or `None` (no lock). The sweep treats `None` as "leave it". New unit cases
   `test_a_filesystem_without_locks_still_makes_a_folder_that_is_never_swept` and
   `test_only_contention_is_busy`. Your `enolck.py` now prints `ran 0 b'1\n'` and leaves nothing
   (`mut2/probes/stepped.txt`). README "Not protected" and the CHANGELOG say so.
3. **Fixed:** the test reads the identity through `private.fd`. The dry run will show the Windows
   path.
4. **Fixed:** `test_another_owner_is_refused` fakes `os.lstat` for the lock path only (a
   `stat_result` with `st_uid = getuid() + 1`; POSIX), and `test_owned_means_this_users` tests
   `_owned` on two `stat_result`s. m01 now fails both.
5. **Fixed:** `test_a_folder_rmtree_could_not_remove_keeps_its_lock_file` (a no-op `rmtree` for
   `remove()`, then a fresh sweep removes both). m03 now fails it.
6. **Fixed (the optional fix):** on POSIX the sweeper unlinks before `_unlock_close`. New case
   `test_the_sweep_unlinks_before_it_lets_the_lock_go`. Your p2 now shows the creator drawing a
   second name while the sweeper holds the first, and the live call keeping its lock file. The
   Windows window stays and is written into Decision 2.
7. **Fixed:** on a difference, `same-bytes` prints each entry found in only one wheel (name,
   mode, size, CRC, date), or says that no entry differs, then exits 1. EXECUTED on two
   hand-made wheels that differ in one entry. The scan of spec 012 still passes (no `||`).
8. **Fixed in part, answered for the rest.** `O_EXCL`:
   `test_an_existing_lock_file_is_never_opened_again` (m13 now fails it). The FIFO test drops
   "without hanging" from its name, and the spec's check list says the check cannot see
   `O_NONBLOCK`. The landing notes name m09, m14 and the layered m07, m08, m10, m11 as not
   separately checked, and why.
9. **Fixed:** the `trapped` comment names every value; the failing-listing case makes a folder
   afterwards (the unit file makes no guest call by design, since it runs without the set in
   the verify job); `_unlock_close` unlocks on Windows before it closes, in `remove()`,
   `_abandon`, the sweep and `_locks_free`; `sysctlbyname` has `argtypes` and `restype`.

Also from section 1: `_call` now makes the stdin folder inside its `try`, so if `_Private`
raises, `store.close()` and the clean-up of the outputs still run.

## Verdict

**Does not land yet.** The design is built as decided:
- creation order, abandon and remove are right;
- the sweep never removed a live call's folder, in real processes, with several sweepers at once
  or with sweepers racing creators;
- the wheel is reproducible across macOS and arm64 Linux;
- the trap names are right and honestly announced.

Three things must change first:
- a creator must redraw, not raise, when a sweeper removes its new lock file (finding 1);
- a temporary folder without locks must not make every call fail (finding 2, a spec decision);
- the unit test that reads a held lock file must not break the Windows verify job (finding 3).

Findings 4 to 9 are cheap, and are best done in the same pass.

One line: the sweep is safe, but the creator must survive the sweep and a lockless folder, and
the Windows test must not read a locked byte.

## Confirmation (2026-10-17)

- **Reviewer:** the build reviewer above (Claude Opus 5.5), not the author.
- **Read:** the dispositions above. I also read the clone's uncommitted `git diff` on `47fc480`:
  the runner, the workflow, the sweep unit file, the v1.4 helper, the README, the CHANGELOG, and
  the specification's new paragraph "A filesystem without locks" with its landing notes.
- **Ran (EXECUTED, same host and set).** Outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev016c/`.
  I did not edit the clone: its `git diff` and its index were byte-equal before and after
  (`clone-diff-before.patch`, `index-before.txt`).
  - `uv run pytest -p no:cacheprovider` in the clone (`pytest-full.txt`) →
    `155/166 pass · 0 gap · 11 blocked · 0 fail (unit suite 338/344, 6 skipped)`; v1.4 `59/59`;
    `493 passed, 17 skipped`; ratchet vs `1abb07264f`: `lost 0 · absent 0 · unrun 0 · unrun
    locally 9 · gained 3 · grew 0`, the judge changed in the same three files; **exit 0**.
    ruff: all checks passed; 47 files already formatted.
  - The new and changed tests (30 now), 5 times idle and 3 times under 20 busy loops: `30 passed`
    every time (`repeat.txt`).
  - My probes, re-run against the clone as it stands (`probes/`).
  - My mutations, re-run with new ones (`mut/mutations.txt`).
  - The new `same-bytes` step, extracted from the workflow by a YAML parser (`yaml/step.sh`) and
    run under `bash -e` in a Linux container on three wheel pairs (`yaml/step-run.txt`).

### Each finding

1. **Closed.**
   - EXECUTED (`probes/stepped.txt`): in p1 the paused creator draws a second name and succeeds;
     in p1run `run` returns 0.
   - The stress run (`probes/p4.txt`) makes 6,000 of 6,000 with `errors {}` and `lost 0`.
   - READ: `owns` is `_same_file`'s answer, so `_abandon` unlinks only a file that is still this
     call's.
   - Mutation n1 (`_same_file` raises again) is caught by the new case. Mutation n6 (`_abandon`
     unlinks whether or not it owns the file) survives. Its harm needs another file at the same
     random name, so I accept it as not checkable at reasonable cost.
2. **Closed. The decision is sound.**
   - READ: an identity is written only when the lock was taken (`if locked and identity`), and
     the sweep treats `None` as "leave it" (`if not _try_lock(fd)`). So a folder made without a
     lock always has an empty first line, and no sweep removes a folder whose first line is not
     its own identity.
   - That holds even when locks come and go. EXECUTED (`probes/nolock-mixed.txt`): a creator
     whose `flock` fails with `ENOLCK` held a call while a sweeper with working locks swept,
     twice, once before and once after the creator was killed. The folder and its stdin stayed
     both times. That is a leak, never a removal, as the new paragraph says.
   - The paragraph's phrase "a sweep on that filesystem cannot take a lock either" is not what
     the safety rests on, since a lock daemon can come back. The empty first line is. Optional
     wording fix: "and even a sweep that can take the lock leaves it, because its first line is
     not an identity".
   - EXECUTED (`probes/enolck.txt`): the earlier `ENOLCK` probe now prints `ran 0 b'1\n'` and
     leaves nothing.
   - Mutations n2 (every lock error is "busy") and n3 (an identity written without a lock) are
     each caught.
   - The README and CHANGELOG say so.
3. **Closed by reading.** The test reads through `private.fd`. Windows is still unrun; the dry run
   is the evidence.
4. **Closed.** m01 is now caught by both new cases (EXECUTED). The fake `lstat` changes only the
   lock path's `st_uid`, and it is POSIX-only with a reason, which is right for a unit test.
5. **Closed.** m03 is caught (EXECUTED). The case also shows that a later sweep removes both.
6. **Closed on POSIX.**
   - EXECUTED (`probes/stepped.txt`, p2): the creator finds the first name locked by the sweeper,
     draws a second, and keeps its own lock file. The sweeper removes only the first.
   - Mutation n4 (unlink after close) is caught.
   - The Windows window is written into Decision 2 as a leak, never a removal. That is acceptable.
7. **Closed.**
   - The YAML parses. The heredoc's terminator lands at column 0 once the block's indentation is
     stripped, and so does the Python.
   - EXECUTED (`yaml/step-run.txt`, `bash -e`, GNU coreutils, Python 3.13): the same wheel →
     `ubuntu-24.04-arm: the same wheel`, exit 0.
   - A changed `runner.py` → two lines naming `wasi_python/runner.py` with the release's and the
     rebuild's size and CRC, exit 1.
   - The same entries with one stored uncompressed → `(no entry differs: the zip's own records
     do)`, exit 1.
   - My run used a shim for `unzip` (the slim image has none). The runner image has Info-ZIP
     `unzip` (INFERRED); `python3` is on ubuntu-24.04 (INFERRED).
   - The `if ! cmp -s` form keeps spec 012's scan green (the judge passes).
8. **Closed or answered.**
   - m13 is caught by the new `O_EXCL` case.
   - m02, m07, m08, m09, m10, m11 and m14 still survive, as the landing notes now say and explain.
   - The FIFO test's name no longer claims "without hanging".
9. **Closed.**
   - The `trapped` comment lists every value.
   - The listing case now goes on to make a folder. That is reasonable, since the unit file runs
     without the set.
   - `_unlock_close` unlocks before closing on Windows. An unlock of a range this handle does not
     hold fails and is ignored (INFERRED: Windows locks belong to the handle that took them, so
     it cannot free another holder's lock).
   - `sysctlbyname` has `argtypes` and `restype`, and the identity still reads.
- **Section 1's note.** The stdin `_Private` now sits inside the `try`, so `store.close()` and the
  output clean-up run if it raises (READ). Mutation n7 (back outside) survives, since nothing
  makes it raise there now. I accept that.

### Did anything new break?

- **POSIX unlink before close in `_sweep_entry`.**
  - No new hazard found (READ, EXECUTED).
  - A second sweeper that gets the lock after the first closes holds an unlinked inode. It finds
    no folder, so its own unlink fails quietly.
  - p3 (`probes/p3.txt`): 10 rounds, 4 sweepers at once, 200 dead and 20 live folders. Each round
    summed to exactly 200 swept, all 40 live entries stayed, and the holder's data was intact.
- **The tri-state `_try_lock`.**
  - Correct as read. On POSIX, only `BlockingIOError` is "busy". On Windows, `EACCES`, `EDEADLK`
    and `EDEADLOCK` are "busy"; `msvcrt.locking` sets `EACCES` for `LK_NBLCK` (INFERRED).
  - If some POSIX filesystem reported contention as `EACCES`, the creator would go on unlocked
    and without an identity. That is a leak, never a removal.
  - `test_only_contention_is_busy` fakes `BlockingIOError` on Windows too, so the Windows
    `EACCES` mapping itself is not unit-checked (nit; a Windows-only case raising
    `PermissionError(errno.EACCES)` would cover it).
- **The scratch `_Private` inside the `try`.** Correct: `scratch` starts as `None`, and the
  `finally` removes it only if it was made.
- **The `same-bytes` heredoc.** It works (finding 7 above).

### New finding

N1. **Nothing checks that the sweep leaves an entry whose lock attempt errors** (`runner.py`, the
    sweep's `if not _try_lock(fd)`). Low.
   - This rule is safety-relevant. A sweeper whose lock attempt fails with `ENOLCK` cannot tell a
     live call from a dead one.
   - EXECUTED (`probes/sweep_enolck.txt`): a folder whose lock file names this kernel, swept while
     `flock` raises `ENOLCK`:
     - the clone keeps it (`swept 0`);
     - mutation n5 (`if _try_lock(fd) is False`) removes it (`swept 1`).
   - n5 passes every check. `test_a_filesystem_without_locks…` uses a folder with an empty first
     line, which the identity check already keeps.
   - Fix: one unit case. Make `dead(temp)` (this kernel's identity), fake `flock` (POSIX) or
     `msvcrt.locking` (Windows) to raise `ENOLCK`, then require `sweep() == 0` and the folder to
     stay.

## Disposition of the confirmation

- **N1, fixed.** `test_a_lock_that_errors_keeps_its_folder`: a dead folder whose lock file names
  this kernel, and a fake `flock` (POSIX) or `msvcrt.locking` (Windows) raising `ENOLCK`; the
  sweep removes nothing and the folder stays. EXECUTED: with the sweep's test changed to
  `_try_lock(fd) is False`, it fails (scratch `build016/mut2/n1/`); with the code as it is, the
  sweep file passes, 27 of 27. The spec's check list names it.
- **The Windows `EACCES` nit, fixed.** `test_only_contention_is_busy` also fakes `EACCES` on
  Windows and requires `False`.
- **The wording, fixed.** Decision 2's "A filesystem without locks" now rests the safety on the
  empty first line, "even by a sweep whose lock works (a lock daemon that comes back)", and says
  a sweep whose own lock attempt errors leaves the entry whatever its first line.

## Verdict of the confirmation

**Confirmed for findings 1 to 9.** Each is closed or answered, and nothing in the revision broke:
- the judge is green;
- the probes, the stress runs and the concurrent sweeps hold;
- the new workflow step behaves on all three cases.

**Still open:** N1, one cheap unit case. The code is already correct; only the check is
missing. The build lands once N1 is fixed or answered in writing. Criterion 3, the dry run, then
shows the Windows path for the first time.

## Follow-up: the Windows dry run (2026-10-17)

A fresh reviewer, who wrote neither the build nor this change, checked one uncommitted judge
change: `tests/unit/test_runner_sweep.py`, the check
`test_a_lock_file_swept_before_its_lock_makes_the_creator_draw_again` (finding 1's check).
Scratch work is under the session scratchpad, `rev016w/`.

### What failed

- The release dry run, run 39044137653, failed `verify (windows-2025)` in this one check and
  nothing else (EXECUTED, `gh run view --log-failed`: 1 failed, 123 passed, 8 skipped; Python
  3.14.2).
- The check's own `lock.unlink()` raised `PermissionError: [WinError 32]`, a sharing violation.
  The creator, `_Private.__init__`, still held the lock file open from its `O_EXCL` creation.
- So the code did not fail; the check could not perform its simulated sweep on Windows.

### 1. Can the race happen on Windows?

No, for the creator's open lock file. The claim holds.
- **How the creator opens (READ, `build/Python-3.15.0/Modules/posixmodule.c:11724`).** On
  Windows, `os.open` calls the C runtime's `_wopen(path, flags, mode)`. It passes no share flag.
- **What that share mode is (INFERRED, from the UCRT's `_wsopen`).** `_wopen` opens with
  `_SH_DENYNO`, which is `FILE_SHARE_READ | FILE_SHARE_WRITE`. `FILE_SHARE_DELETE` is added only
  for `_O_TEMPORARY`, which the runner does not use (READ, `_Private.__init__`: `O_RDWR`,
  `O_CREAT`, `O_EXCL`, `O_BINARY`; the POSIX-only flags are 0 there).
- **What that means.** Deleting a file opens it for `DELETE` access. While any handle lacks
  `FILE_SHARE_DELETE`, that open fails with error 32. This holds for another process and for the
  same process, which is what the dry run showed (EXECUTED, in CI). Windows' newer POSIX-style
  delete does not change this: it still needs that `DELETE` open first (INFERRED).
- **No gap at creation (INFERRED).** `O_CREAT | O_EXCL` maps to `CREATE_NEW`, which creates and
  opens in one call. The file never exists without the creator's handle until `_abandon` or
  `remove` closes it.
- **The sweeper (READ, `_sweep_entry`).** On Windows it closes its own handle first, then calls
  `_unlink_quietly`. That unlink fails on a creator's open file and is swallowed. So the sweeper
  cannot remove a creator's new lock file while the creator holds it.
- **The one Windows path left, and it is benign (INFERRED).** A sweeper can take the lock on a
  creator's new, empty file before the creator does. Then:
  - the creator's `_try_lock` returns `False`, so it raises `_Taken` with `owns` still `False`;
  - `_abandon` closes without unlinking, and the creator draws a new name;
  - the sweeper's later unlink fails if the creator has not closed yet.

  The result is a lone, empty lock file. A later sweep removes it under the lone-lock rule.
  Nothing raises out of `run` and no data is lost. POSIX has the same window, but its sweeper
  unlinks while still holding the lock, so nothing is left there. Not a finding.
- **Out of scope (INFERRED).** A `%TEMP%` on a network share relies on the server's share-mode
  enforcement. That is not a supported layout for a per-user temporary folder here.

### 2. Does the check still guard finding 1 on POSIX?

Yes (EXECUTED, macOS). The check ran against copies of `src/` on `PYTHONPATH`; each run printed
the copy's `runner.__file__` to prove the copy was the one imported.

| copy | change to the runner | result |
|------|----------------------|--------|
| `m0` | none | passes |
| `m1` | `_same_file` without its `try`: raises on a missing path (finding 1's bug) | **fails**: `FileNotFoundError` out of `_Private` |
| `m2` | `_same_file` always `True` | **fails**: the creator kept the swept name |
| `m3` | the creator ignores `owns` (`owns = True`) | **fails**: the creator kept the swept name |

- On POSIX the `unlink` succeeds, so the check takes the old branch, unchanged in substance.
- If an `unlink` ever raised `PermissionError` on POSIX, the check would not pass quietly
  (EXECUTED, `w1`: a scratch copy of the check whose `unlink` raises fails on
  `assert os.name == "nt"`).
- It also adapts by itself. If Windows ever let the file be deleted, the check would take the
  POSIX branch there and test the redraw.

### 3. Does the Windows branch assert something real?

Yes (EXECUTED by simulation, `w2`, since no Windows host was run here). The scratch copy `w2`
makes `unlink` raise `PermissionError` and waives the `os.name` check.
- Against the real runner it passes.
- Against `m4`, a runner whose creator redraws once even though its file is still there, it
  **fails**: `assert 3 == 2`, the abandoned first lock file plus the second name's folder and
  lock.

So `len(names(temp)) == 2` is right. It is the folder and its one lock file, and it tells "kept
its first name" from "redrew". It also shows that `_same_file` is `True` for a file that is still
there on Windows; otherwise every draw would fail.

Nit (not blocking): record the lock file's name in both branches. The Windows branch could then
assert `Path(private.lock_path).name == first`, which says "its first name" directly rather than
by a count.

### 4. The judge

- `uv run pytest -q tests/unit/test_runner_sweep.py`: 27 passed (EXECUTED).
- `ruff check src tests`: clean. `ruff format --check src tests`: 47 files already formatted
  (EXECUTED).
- `uv run pytest -m "not slow"` (EXECUTED): 158/166, 0 fail, unit suite 345/345; ratchet `lost 0 ·
  gained 0 · grew 0`; `judge changed: tests/unit/test_runner_sweep.py`. Acceptance therefore needs
  `--accept-judge` with a reason.
- The change edits a check. It does not weaken it: on POSIX it fails on every mutation above, as
  before. On Windows it replaces a crash of the check itself with a real assertion, and it adds no
  skip.

### Verdict

**Lands.** The Windows claim is right for how CPython opens the creator's file. Finding 1's guard
on POSIX is intact. The Windows branch checks a real property. The one nit is optional. Accept it
with `--accept-judge`, naming this follow-up, and confirm on the next Windows dry run.

### Disposition of the follow-up (filled in by the author)

- The nit is taken: the Windows branch records the first lock file's name and asserts the
  creator kept it, instead of counting entries.
